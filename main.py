from flask import Flask, request, jsonify
from sqlalchemy.orm import sessionmaker
from database import engine, init_database
from models import Question, Session
import requests
import random
import json

app = Flask(__name__)
SessionLocal = sessionmaker(bind=engine)

# Инициализируем базу данных при запуске
init_database()

def get_map_image(lat, lon, city_name):
    """Получает статическое изображение карты с меткой"""
    api_key = "YOUR_YANDEX_MAPS_API_KEY"  # Замените на ваш API‑ключ
    url = f"https://static-maps.yandex.ru/1.x/?"
    params = {
        'll': f"{lon},{lat}",
        'spn': '0.1,0.1',
        'l': 'map',
        'pt': f"{lon},{lat},pm2rdm",
        'size': '450,300',
        'lang': 'ru_RU'
    }
    return url + "&".join([f"{k}={v}" for k, v in params.items()])

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.json
    user_id = req['session']['user']['userId']
    db = SessionLocal()
    
    # Получаем или создаём сессию пользователя
    user_session = db.query(Session).filter_by(user_id=user_id).first()
    if not user_session:
        user_session = Session(user_id=user_id)
        db.add(user_session)
        db.commit()
    
    response_text = ""
    response_card = None
    
    # Обрабатываем команды
    if 'start' in req['request']['command'].lower():
        response_text = "Привет! Добро пожаловать в викторину по Marvel! Выбери режим: 5 или 10 вопросов?"
        user_session.score = 0
        user_session.current_question = 0
        user_session.questions_asked = []
    
    elif '5' in req['request']['command'] or '10' in req['request']['command']:
        user_session.total_questions = int(req['request']['command'])
        response_text = f"Отлично! Игра на {user_session.total_questions} вопросов начинается! Первый вопрос:"
        # Задаём первый вопрос
        next_question = get_random_question(db, user_session)
        response_text += " " + next_question.text
        if next_question.question_type == 'city':
            map_url = get_map_image(next_question.latitude, next_question.longitude, next_question.city_name)
            response_card = {
                "type": "BigImage",
                "image_id": map_url,
                "title": next_question.text,
                "description": f"Город: {next_question.city_name}"
            }
    
    elif user_session.current_question < user_session.total_questions:
        # Проверяем ответ
        user_answer = req['request']['command'].lower()
        current_question_id = user_session.questions_asked[-1]
        current_question = db.query(Question).filter_by(id=current_question_id).first()
        
        if user_answer == current_question.correct_answer.lower():
            user_session.score += 1
            response_text = "Правильно! "
        else:
            response_text = f"Неверно. Правильный ответ: {current_question.correct_answer}. "
        
        # Следующий вопрос или конец игры
        if user_session.current_question < user_session.total_questions - 1:
            next_question = get_random_question(db, user_session)
            response_text += "Следующий вопрос: " + next_question.text
            if next_question.question_type == 'city':
                map_url = get_map_image(next_question.latitude, next_question.longitude, next_question.city_name)
                response_card = {
                    "type": "BigImage",
                    "image_id": map_url,
                    "title": next_question.text,
                    "description": f"Город: {next_question.city_name}"
                }
        else:
            # Конец игры
            response_text = f"Игра окончена! Ваш результат: {user_session.score} из {user_session.total_questions}. Хотите сыграть ещё раз?"
            user_session.score = 0
            user_session.current_question = 0
            user_session.questions_asked = []
    
    def get_random_question(db, user_session):
    """Получает случайный вопрос, который ещё не задавался"""
    asked_ids = user_session.questions_asked
    available_questions = db.query(Question).filter(
        Question.id.notin_(asked_ids)
    ).all()
    
    if not available_questions:
        # Если все вопросы заданы, начинаем заново
        user_session.questions_asked = []
        available_questions = db.query(Question).all()
    
    
    question = random.choice(available_questions)
    user_session.questions_asked.append(question.id)
    user_session.current_question += 1
    db.commit()
    return question

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.json
    user_id = req['session']['user']['userId']
    db = SessionLocal()

    # Получаем или создаём сессию пользователя
    user_session = db.query(Session).filter_by(user_id=user_id).first()
    if not user_session:
        user_session = Session(user_id=user_id)
        db.add(user_session)
        db.commit()

    response_text = ""
    response_card = None
    end_session = False

    # Обрабатываем команды
    if 'start' in req['request']['command'].lower() or 'начнем' in req['request']['command'].lower():
        response_text = "Привет! Добро пожаловать в викторину по Marvel! Выбери режим: 5 или 10 вопросов?"
        user_session.score = 0
        user_session.current_question = 0
        user_session.questions_asked = []
        db.commit()

    elif '5' in req['request']['command'] or '10' in req['request']['command']:
        user_session.total_questions = int(req['request']['command'])
        response_text = f"Отлично! Игра на {user_session.total_questions} вопросов начинается! Первый вопрос:"
        # Задаём первый вопрос
        next_question = get_random_question(db, user_session)
        response_text += " " + next_question.text
        if next_question.question_type == 'city':
            map_url = get_map_image(next_question.latitude, next_question.longitude, next_question.city_name)
            response_card = {
                "type": "BigImage",
                "image_id": map_url,
                "title": next_question.text,
                "description": f"Город: {next_question.city_name}"
            }
        db.commit()

    elif user_session.current_question > 0 and user_session.current_question <= user_session.total_questions:
        # Проверяем ответ
        user_answer = req['request']['command'].lower().strip()
        current_question_id = user_session.questions_asked[-1]
        current_question = db.query(Question).filter_by(id=current_question_id).first()

        if user_answer == current_question.correct_answer.lower().strip():
            user_session.score += 1
            response_text = "Правильно! "
        else:
            response_text = f"Неверно. Правильный ответ: {current_question.correct_answer}. "

        # Следующий вопрос или конец игры
        if user_session.current_question < user_session.total_questions:
            next_question = get_random_question(db, user_session)
            response_text += "Следующий вопрос: " + next_question.text
            if next_question.question_type == 'city':
                map_url = get_map_image(next_question.latitude, next_question.longitude, next_question.city_name)
                response_card = {
                    "type": "BigImage",
                    "image_id": map_url,
                    "title": next_question.text,
                    "description": f"Город: {next_question.city_name}"
                }
        else:
            # Конец игры
            response_text = f"Игра окончена! Ваш результат: {user_session.score} из {user_session.total_questions}. Хотите сыграть ещё раз?"
            user_session.score = 0
            user_session.current_question = 0
            user_session.questions_asked = []
            end_session = True
        db.commit()

    else:
        response_text = "Не понимаю команду. Скажите 'начать' для старта игры или выберите количество вопросов (5 или 10)."

    db.close()

    # Формируем ответ для Алисы
    response = {
        "version": req['version'],
        "session": req['session'],
        "response": {
            "text": response_text,
            "end_session": end_session
        }
    }

    if response_card:
        response['response']['card'] = response_card

    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
