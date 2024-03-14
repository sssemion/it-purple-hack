# it-purple-hack


### Как сетапить парсер
Установка зависимостей

- Установить tesseract по [инструкции](https://textract.readthedocs.io/en/stable/installation.html)

- Скачайте языковые пакеты Tesseract:
    - Перейдите на страницу репозитория Tesseract на GitHub: https://github.com/tesseract-ocr/tessdata
    - Скачайте файл rus.traineddata для русского языка.
- Добавьте языковые пакеты в Tesseract:
    - Скопируйте скачанный файл rus.traineddata в директорию с языковыми пакетами Tesseract на вашей системе. (macos: `/opt/homebrew/Cellar/tesseract/<version>/share/tessdata`)

Сетапим окружение

```bash
cd /path/to/project/it-purple-hack
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Запустим парсинг:
```bash
# Правовые акты
python3.11 data/parse/cbr/legal_acts.py

# Базовые стандарты
python3.11 data/parse/cbr/basic_standards.py

# FAQ & explan
python3.11 data/parse/cbr/faq.py
```
Создадутся csv-файлы с соответсвующими названиями в корне проекта

ClickHouse хранилище:
- Можно подключиться с доступами на чтение
  - host: `62.84.115.43`
  - port: `8123`
  - user: `viewer`
  - password: `viewer`
  - database: `dev`
