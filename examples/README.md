<h1>Инструкция по ollama</h1>
<h2>Установка</h2>
Инструкция по установке на Мак и Виндовс находится по ссылке:<br>

https://ollama.com/download
<br>
Если ОС линукс:

```sh
curl -fsSL https://ollama.com/install.sh | sh
```

Чтобы проверить, что всё установилось, необходимо перейти на порт 11434:

http://localhost:11434/

И вы увидите там:
```
Ollama is running
```

<h2>Запуск ollama</h2>
Чтобы запустить ollama модель, надо ознакомиться со списком уже имющихся моделей:

https://ollama.com/library

Инструкция по запуску будет доступна на странице.
Пример:

```sh
ollama run llama2
```

После этой команды вы попадёте в чат с моделью и сможете спокойно задавать ей свои вопросы.

<h2>ollama + litellm</h2>
Для запуска через litellm, необходимо установить библиотеку:

```sh
pip install litellm
```

Создать питоновский файл и вставить в него программу ниже

```python
from litellm import completion

response = completion(
    model="ollama/llama2", 
    messages=[
        { "content": "Напиши анекдот","role": "user"}
    ], 
    api_base="http://localhost:11434"
)
print(response['choices'][0]['message']['content'])
```

Для того чтобы задать свой вопрос, вам в "content" надо передать свой запрос (6 строчка)

<h2>ollama + webui</h2>

В самом начале необходимо запустить контейнер с webui:

```sh
docker run -d --network=host \
    -v open-webui:/app/backend/data \
    -e OLLAMA_BASE_URL=http://127.0.0.1:11434 \
    --name open-webui \
    --restart always ghcr.io/open-webui/open-webui:main
```
Затем необходимо перейти по порту 3000:

http://localhost:3000/