from transformers import PreTrainedTokenizer, PreTrainedModel
import torch

class ToxicityClassifier:
    def __init__(self, tokenizer: PreTrainedTokenizer, model: PreTrainedModel):
        self._model = model
        self._tokenizer = tokenizer
        self.truncation = True
        self.padding = True

    def is_toxic(self, text: str, tresh: int=0.4) -> str:
        with torch.no_grad():
            inputs = self._tokenizer(text,
                                     return_tensors='pt',
                                     truncation=self.truncation,
                                     padding=self.padding).to(self._model.device)
            
            proba = torch.sigmoid(self._model(**inputs).logits).cpu().numpy()
        if isinstance(text, str):
            proba = proba[0]
            
        proba = 1 - proba.T[0] * (1 - proba.T[-1])
        
        if proba <= tresh:
            return "not toxic"
        else:
            return "toxic"