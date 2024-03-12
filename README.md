# it-purple-hack


### Как сетапить парсер
Установка зависимостей

- Установить tesseract по [инструкции](https://textract.readthedocs.io/en/stable/installation.html)

- Скачайте языковые пакеты Tesseract:
    - Перейдите на страницу репозитория Tesseract на GitHub: https://github.com/tesseract-ocr/tessdata
    - Скачайте файл rus.traineddata для русского языка.
- Добавьте языковые пакеты в Tesseract:
    - Скопируйте скачанный файл rus.traineddata в директорию с языковыми пакетами Tesseract на вашей системе. (macos: `/opt/homebrew/Cellar/tesseract/<version>/share/tessdata`)