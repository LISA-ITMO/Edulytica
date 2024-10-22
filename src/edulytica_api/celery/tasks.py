import celery
from celery import Celery
import json
import os
import uuid
from pathlib import Path
import datetime
from src.edulytica_api.crud.result_files_crud import ResultFilesCrud
from src.edulytica_api.crud.tickets_crud import TicketsCrud
from src.edulytica_api.database import SessionLocal
from src.edulytica_api.llms.llm_model import Conversation, LLM
from celery.signals import celeryd_after_setup

app = Celery('tasks')
app.config_from_object('src.edulytica_api.celery.celeryconfig')


# print(__name__)
@celeryd_after_setup.connect()
def set_model_id(sender, instance, **kwargs):
    global DEFAULT_MESSAGE_TEMPLATE
    global DEFAULT_RESPONSE_TEMPLATE
    global SUMMARIZE_DEFAULT_SYSTEM_PROMPT
    global EXTRACT_DEFAULT_SYSTEM_PROMPT
    global PURPOSE_DEFAULT_SYSTEM_PROMPT
    global purpose_llm
    global summarize_llm
    global ROOT_DIR

    DEFAULT_MESSAGE_TEMPLATE = "<|start_header_id|>{role}<|end_header_id|>{content}<|eot_id|>"
    DEFAULT_RESPONSE_TEMPLATE = "<|begin_of_text|>"
    SUMMARIZE_DEFAULT_SYSTEM_PROMPT = '''Ты опытный преподаватель университета, твоя задача делать суммаризацию научных текстов.
                                       Суммаризируй часть научной работы, сохрани основные пункты, главные факты, термины и выводы.
                                       Твой ответ должен быть кратким, содержать от 10 до 15 предложений.
                                       Не добавляй в ответ ничего от себя, опирайся только на исходный текст.
                                       Вот научный текст для суммаризации:'''

    EXTRACT_DEFAULT_SYSTEM_PROMPT = '''Ты ассистент. Твоя задача - анализировать предоставленный текст и выявлять из него конкретные цели и задачи. Цели представляют собой конечные результаты, которых стремится достичь автор текста, а задачи - это конкретные действия или шаги, которые необходимо выполнить для достижения этих целей. Обрати внимание на следующие правила:
                                    Не придумывай цели и задачи, которых нет в тексте: Тебе запрещено добавлять собственные интерпретации или домыслы. Твои выводы должны строго основываться на информации, представленной в тексте.
                                    Отчет о невозможности выявления целей или задач: Если в тексте не удается определить ни цели, ни задачи, ты должен явно указать это в своем отчете. Напиши, что цели или задачи не были выявлены.
                                    Разделение целей и задач: В тексте могут присутствовать только цели, только задачи, или и то, и другое. Важно различать эти категории и правильно их классифицировать.
                                    Процесс выявления целей и задач должен быть систематичным и логичным. Прежде чем писать отчет, внимательно прочитай текст несколько раз, чтобы полностью понять его содержание и контекст. Используй ключевые слова и фразы, которые могут указывать на намерения или план действий.
                                    Примеры: Цель: "Увеличить прибыль компании на 20% в следующем году." Задача: "Разработать и внедрить новую маркетинговую стратегию к концу текущего квартала."
                                    Пример структурированного отчета: 
                                    Цели:
                                    Увеличить прибыль компании на 20% в следующем году. 
                                    Задачи:
                                    Разработать и внедрить новую маркетинговую стратегию к концу текущего квартала.
                                    Провести обучение сотрудников новым методам продаж.
                                    Отчет при отсутствии целей или задач:
                                    Цели: не выявлены. 
                                    Задачи: не выявлены.
                                    Приступай к выполнению задачи, внимательно следуя этим инструкциям.'''

    PURPOSE_DEFAULT_SYSTEM_PROMPT = '''Ты - ассистент преподавателя, который оценивает научную работу. Как и в любой работе, в тексте есть цели и задачи работы. Цель обычно одна, а задач - несколько. Твоя задача просмотреть и проанализировать весь текст работы и оценить соответствие текста поставленной цели и задачам. Тебе нужно проверить, соответствует ли текст поставленной цели и задачам. Если цель или задачи отсутствуют - так и напиши, что задачи не найдены. Также удели внимание источникам информации. Проанализируй их, на сколько они актуальны и применены в этой работе. \
                                    \
                                    Для этого следуй данному плану:\
                                        1. Сначала тебе будет дан текст работы ('all_text' или 'Текст работы'), где будет вся работа (весь текст для анализа), затем будут будут указаны цель и задачи ('goals' или 'Цели работы'), возможно методы исследования и гипотезы,  - определи эти части и проанализируй их;\
                                        2. Прочитай и проанализируй цель и задачи ('goals' или Цели работы), запомни их;\
                                        3. Прочитай и проанализируй весь текст ('all_text' или 'Текст работы'), запомни его;\
                                        4. Проанализируй соответствие цели и задач, а также гипотезы и методы исследования (при наличии) ('goals' или Цели работы), тексту работы ('all_text' или 'Текст работы');\
                                        5. Оцени соответствие текста поставленной цели и задачам. Делай оценку конкретной и объективной, с примерами (подробнее про это будет в правилах ниже);\
                                        6. Сделай подробный отчет.\
                                    \
                                    Обрати внимание на следующие правила: \
                                      1. Не придумывай цели и задачи, которых нет в тексте: Тебе запрещено добавлять собственные интерпретации или домыслы. Твои выводы должны строго основываться на информации, представленной в тексте (all_text и goals).\
                                      2. Если увидишь, что в тексте есть информация, которая не содержится в цели и задачах, выдели ее в отчете, как некорректные данные.\
                                      3. Поскольку задачи и цель могут формулироваться разными вариантами, учти небольшую погрешность в отклонениях.\
                                      4. Процесс определения соответствия текста цели и задачам должен быть систематичным и логичным. Прежде чем писать отчет, внимательно прочитай текст несколько раз, чтобы полностью понять его содержание и контекст. Используй ключевые слова и фразы, которые могут указывать на намерения или план действий.\
                                      5. Оценив текст на соответствие поставленной цели и задачам, укажи в отчете подробно, что сделано правильно, а что нет. В этой задаче постарайся как похвалить автора, так и дать какие-то рекомендации по исправлениям, если они требуются.\
                                      6. В последнем пункте отчета попробуй сделать численную оценку в процентах на соответствие цели и задачам и объясни, почему оценка именно такая.\
                                      7. Заметь, что в тексте написаны цель и задачи. Тебе нужно найти цель и задачи, затем прочитать и проанализировать весь текст и, после этого, сравнить текст на соответствие цели и задачам, которые присутствуют в тексте.\
                                      8. Важно! Не допускай повторений. Каждое из требований ты должен выполнить один раз. Например, не делай больше 1 раза численную оценку в процентах, это нужно сделать только 1 раз в конце отчета. Тоже самое и с другими пунктами, повторений быть не должно! Твой ответ должен быть последовательным и структурированным, а также логически выстроенным.'''

    purpose_llm = LLM('IlyaGusev/saiga_llama3_8b', 'slavamarcin/saiga_llama3_8b-qdora-4bit_purpose')
    summarize_llm = LLM('IlyaGusev/saiga_llama3_8b', 'slavamarcin/saiga3_8b_Qdora_4bit_sum')
    ROOT_DIR = Path(__file__).resolve().parents[1]


def chunk_text(text, chunk_size, overlap):
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Некорректные параметры: размер чанка должен быть положительным числом, "
                         "нахлёст должен быть неотрицательным числом и меньше размера чанка.")

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap

        if start >= text_length:
            break

    return chunks


class Task(celery.Task):
    def __init__(self):
        self.sessions = {}

    def before_start(self, task_id, args, kwargs):
        self.sessions[task_id] = SessionLocal()
        super().before_start(task_id, args, kwargs)

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        session = self.sessions.pop(task_id)
        session.close()
        super().after_return(status, retval, task_id, args, kwargs, einfo)

    @property
    def session(self):
        return self.sessions[self.request.id]


@app.task(bind=True, base=Task)
def get_llm_purpose_result(self, intro, main_text, user_id, ticket_id):
    def prepare_answer(all_text, goals):
        PROMPT_TEMPLATE = "Текст работы:\n{all_text}\n\nЦели работы:\n{goals}\n\n"
        combined_text = PROMPT_TEMPLATE.format(all_text=all_text, goals=goals)
        chunks = chunk_text(combined_text, 12000, 0)
        purpose_conversation = Conversation(message_template=DEFAULT_MESSAGE_TEMPLATE,
                                            response_template=DEFAULT_RESPONSE_TEMPLATE,
                                            system_prompt=PURPOSE_DEFAULT_SYSTEM_PROMPT)
        for i, chunk in enumerate(chunks):
            if i == len(chunks) - 1:
                purpose_conversation.add_user_message(chunk)
        prompt = purpose_conversation.get_prompt(purpose_llm.tokenizer)
        out = purpose_llm.generate(prompt)
        return out

    try:
        extract_conversation = Conversation(message_template=DEFAULT_MESSAGE_TEMPLATE,
                                            response_template=DEFAULT_RESPONSE_TEMPLATE,
                                            system_prompt=EXTRACT_DEFAULT_SYSTEM_PROMPT)
        extract_conversation.add_user_message(intro)
        prompt = extract_conversation.get_prompt(purpose_llm.tokenizer)
        goals = purpose_llm.generate(prompt)
        result_data = prepare_answer(main_text, goals)

        result = {'goal': goals, 'result': result_data}
        file_id = uuid.uuid4()
        current_date = datetime.date.today().isoformat()
        os.makedirs(os.path.join(ROOT_DIR, 'results_file', current_date), exist_ok=True)
        file_path = os.path.join(ROOT_DIR, 'results_file', current_date, str(file_id) + '.json')
        file_path_bd = os.path.join('results_file', current_date, str(file_id) + '.json')
        with open(file_path, 'w+', encoding='utf-8') as file:
            json.dump(result, file)
        ResultFilesCrud.create(session=self.session, file=file_path_bd, user_id=user_id, ticket_id=ticket_id)
        TicketsCrud.update(session=self.session, record_id=ticket_id, status_id=1)
        return {'result': 'ok', 'intro': intro}
    except Exception as e:
        TicketsCrud.update(session=self.session, record_id=ticket_id, status_id=2)
        raise e


@app.task(bind=True, base=Task)
def get_llm_summary_result(self, main_text, user_id, ticket_id):
    def prepare_answer(all_text):
        result_data = {}
        for i, inpt in enumerate(all_text):
            print(inpt)
            summarize_conversation = Conversation(message_template=DEFAULT_MESSAGE_TEMPLATE,
                                                  response_template=DEFAULT_RESPONSE_TEMPLATE,
                                                  system_prompt=SUMMARIZE_DEFAULT_SYSTEM_PROMPT)
            summarize_conversation.add_user_message(inpt)
            prompt = summarize_conversation.get_prompt(summarize_llm.tokenizer)
            output = summarize_llm.generate(prompt)
            result_data[i] = [output]
        return result_data

    try:
        result_data = prepare_answer(main_text)
        file_id = uuid.uuid4()
        current_date = datetime.date.today().isoformat()
        os.makedirs(os.path.join(ROOT_DIR, 'results_file', current_date), exist_ok=True)
        file_path = os.path.join(ROOT_DIR, 'results_file', current_date, str(file_id) + '.json')
        file_path_bd = os.path.join('results_file', current_date, str(file_id) + '.json')
        result = {'result': result_data}
        with open(file_path, 'w+', encoding='utf-8') as file:
            json.dump(result, file)
        ResultFilesCrud.create(session=self.session, file=file_path_bd, user_id=user_id, ticket_id=ticket_id)
        TicketsCrud.update(session=self.session, record_id=ticket_id, status_id=1)
        return {'result': 'ok'}
    except:
        TicketsCrud.update(session=self.session, record_id=ticket_id, status_id=2)
        return {'result': 'error'}
