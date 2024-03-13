from nltk.tokenize import sent_tokenize
import pandas as pd
import numpy as np


class Chunker:
    def __init__(self, max_chunk_len=2500, overlap_len=50):
        self._max_chunk_len = max_chunk_len
        self._overlap_len = overlap_len
        self._tokenizer = sent_tokenize

    @staticmethod
    def _join_docs(docs, separator):
        text = separator.join(docs).strip()
        if text == "":
            return None
        else:
            return text

    def create_chunks(self, text, url, separator='\n'):
        sep_len = len(separator)
        tokenized_text = self._tokenizer(text, language='russian')
        chunks = []
        cur_chunk = []
        total_len = 0

        for sentence in tokenized_text:
            sentence_len = len(sentence)
            if total_len + sentence_len + (sep_len if len(cur_chunk) > 0 else 0) > self._max_chunk_len:
                if total_len > self._max_chunk_len:
                    pass
                if len(cur_chunk) > 0:
                    doc = self._join_docs(cur_chunk, separator)
                    if doc is not None:
                        chunks.append(doc)

                    while (total_len > self._overlap_len or
                           (total_len + sentence_len + (sep_len if len(cur_chunk) > 0 else 0) > self._max_chunk_len and
                            total_len > 0)):
                        total_len -= len(cur_chunk[0]) + (sep_len if len(cur_chunk) > 1 else 0)
                        cur_chunk = cur_chunk[1:]
            cur_chunk.append(sentence)
            total_len += sentence_len + (sep_len if len(cur_chunk) > 1 else 0)

        doc = self._join_docs(cur_chunk, separator)

        if doc is not None:
            chunks.append(doc)
        urls = [url] * len(chunks)
        return chunks, urls

    def split_texts(self, texts):
        chunks = []
        urls = []
        for ind, text in texts.iterrows():
            cur_chunks, cur_urls = self.create_chunks(text.text, text.name)
            chunks.extend(cur_chunks)
            urls.extend(cur_urls)
        return chunks, urls
        

class Retriever:
    def __init__(self, retriever_model, reranker_model, clickhouse_client):
        self._client = clickhouse_client
        self._retriever_model = retriever_model
        self._reranker_model = reranker_model
        self._query = """
        WITH similar_chunks AS (
            SELECT 
                c1.chunk_uuid AS similar_uuid,
                c1.{model}_embedding AS similar_embedding,
                cosineDistance({model}_embedding, {question_embedding}) AS similarity_score
            FROM 
                chunk_embedding c1
            ORDER BY 
                similarity_score ASC
            LIMIT {knn_k})
        SELECT 
            c.uuid AS uuid,
            c.text AS text,
            c.url AS url
        FROM 
            chunk c
        JOIN 
            similar_chunks s 
        ON 
            c.uuid = s.similar_uuid
        WHERE
            c.uuid IN (SELECT similar_uuid FROM similar_chunks)
        """
        
    def get_neighbors(self, question, k=5):
        topk = None
        e5_embedding = self._retriever_model.encode(question, batch_size=16, normalize_embeddings=True)
        e5_query = self._query.format(question_embedding=e5_embedding.tolist(), knn_k=k, model='e5')
        e5_topk = self._client.query_df(e5_query).set_index('uuid')  
        
        bge_embedding = self._reranker_model.encode(question, 
                                                    return_dense=True, 
                                                    return_sparse=False, 
                                                    return_colbert_vecs=True, 
                                                    batch_size=16, 
                                                    max_length=512)
        
        bge_query = self._query.format(question_embedding=bge_embedding['dense_vecs'].tolist(), knn_k=k, model='bge_m3')
        bge_topk = self._client.query_df(bge_query).set_index('uuid') 
        topk = pd.concat([e5_topk, bge_topk]).drop_duplicates(keep='first')
                
        return topk.text.tolist(), topk.url.tolist(), bge_embedding['colbert_vecs']
    
    def rerank(self, question_embedding, documents, top_k):
        topk_colbert = self._reranker_model.encode(documents, 
                                                   return_dense=False, 
                                                   return_sparse=False, 
                                                   return_colbert_vecs=True, 
                                                   batch_size=16, 
                                                   max_length=512)['colbert_vecs']
        scores = np.zeros((len(topk_colbert), ))
        for ind, sample in enumerate(topk_colbert):
            scores[ind] = -self._reranker_model.colbert_score(question_embedding, sample)
        
        return scores.argsort()[:top_k]
    
    @staticmethod
    def get_topk(documents, urls, indexes):
        return [documents[i] for i in indexes], list(set(urls[i] for i in indexes))
