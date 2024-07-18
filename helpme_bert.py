import numpy as np
import pandas as pd
from numpy import dot
from numpy.linalg import norm
from sentence_transformers import SentenceTransformer
import os
import speech_recognition as sr
import pandas as pd

def class_init():
    os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

    train_data = pd.read_excel("/Users/eunseo/PycharmProjects/chatbot_telegram/helpme/240710/detailed_split_data.xlsx")
    train_data = train_data.iloc[:, :3]

    model = SentenceTransformer('jhgan/ko-sbert-sts')

    train_data['embedding_Q1'] = train_data.apply(lambda row: model.encode(row.Q1), axis=1)
    train_data['embedding_Q2'] = train_data.apply(lambda row: model.encode(row.Q2), axis=1)
    return model, train_data

def cos_sim(A, B):
    return dot(A, B) / (norm(A) * norm(B))

class Chatbot:
    def __init__(self, model, data):
        self.model = model
        self.data = data
        self.state = 'INITIAL'
        self.selected_topic = None

    def reset(self):
        self.state = 'INITIAL'
        self.selected_topic = None

    def get_topic_or_subtopic(self, question):
        embedding = self.model.encode(question)
        self.data['score_Q1'] = self.data.apply(lambda x: cos_sim(x['embedding_Q1'], embedding), axis=1)
        self.data['score_Q2'] = self.data.apply(lambda x: cos_sim(x['embedding_Q2'], embedding), axis=1)

        best_match_Q1 = self.data.loc[self.data['score_Q1'].idxmax()]
        best_match_Q2 = self.data.loc[self.data['score_Q2'].idxmax()]

        if best_match_Q2['score_Q2'] >= best_match_Q1['score_Q1']:
            return 'SUBTOPIC', best_match_Q2
        else:
            return 'TOPIC', best_match_Q1

    def get_subtopics(self, topic):
        subtopics = self.data[self.data['Q1'] == topic]['Q2'].unique()
        return subtopics

    def get_answer(self, topic, subtopic):
        answer = self.data[(self.data['Q1'] == topic) & (self.data['Q2'] == subtopic)]['A'].values[0]
        return answer

    def respond(self, user_input):
        if self.state == 'INITIAL':
            match_type, best_match = self.get_topic_or_subtopic(user_input)
            if match_type == 'SUBTOPIC':
                answer = best_match['A']
                return answer, []
            else:
                self.selected_topic = best_match['Q1']
                subtopics = self.get_subtopics(self.selected_topic)
                if 'default' in subtopics:
                    default_answer = self.get_answer(self.selected_topic, 'default')
                    subtopics = [sub for sub in subtopics if sub != 'default']
                    if subtopics:
                        return default_answer, subtopics
                    else:
                        return default_answer, []
                else:
                    self.state = 'WAITING_FOR_SUBTOPIC'
                    print(subtopics)
                    return None, subtopics

        elif self.state == 'WAITING_FOR_SUBTOPIC':
            subtopics = self.get_subtopics(self.selected_topic)
            if user_input in subtopics:
                answer = self.get_answer(self.selected_topic, user_input)
                self.state = 'INITIAL'
                return answer, []
            else:
                return f"'{user_input}' 키워드에 대한 답변을 찾을 수 없습니다. 다시 시도해주세요.", []

def chatbot_init():
    model, train_data = class_init()
    bot = Chatbot(model, train_data)
    return bot

# 음성 수신, 형태소 분석 함수
def totext(data, num):  # 텔레그램 대화로부터 고객에게 받은 메시지와 메시지의 형식(0 or 1)을 입력으로 받아 키워드를 추출
    if num == 0:  # 들어온 data가 음성파일이라면
        recognizer = sr.Recognizer()  # 음성인식 객체 생성
        with sr.AudioFile(data) as source:  # data를 음성파일로써 열고, source에 담음
            audio_data = recognizer.record(source)  # source의 오디오데이터를 녹음하여 audio_data에 담음
            try:
                query = recognizer.recognize_google(audio_data, language='ko-KR')  # audio_data의 오디오 데이터를 한국어로 음성 인식 수행
            except sr.UnknownValueError:  # 음성을 인식할 수 없는 경우 에러 메시지
                print("음성을 인식할 수 없습니다.")
            except sr.RequestError as e:  # 음성인식 서비스에 문제가 생긴 경우 에러메시wl
                print(f"음성 인식 서비스에 문제가 있습니다: {e}")
    elif num == 1:  # 들어온 data가 텍스트 형태라면
        query = data  # 데이터 처리 없이 pass

    return query

