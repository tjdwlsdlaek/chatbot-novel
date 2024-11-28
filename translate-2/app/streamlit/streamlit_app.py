import streamlit as st
from websocket import WebSocketApp
import json
import threading
import time
import os

# API Gateway URL을 환경 변수에서 가져옵니다.
API_GATEWAY_URL = os.environ.get('API_GATEWAY_URL')
if not API_GATEWAY_URL:
    st.error("API Gateway URL is not set. Please set the API_GATEWAY_URL environment variable.")
    st.stop()

# WebSocket 연결 및 메시지 처리를 위한 클래스
class WebSocketClient:
    def __init__(self, url):
        self.url = url
        self.ws = None

    def connect(self):
        self.ws = WebSocketApp(self.url,
                               on_message=self.on_message,
                               on_error=self.on_error,
                               on_close=self.on_close,
                               on_open=self.on_open)
        threading.Thread(target=self.ws.run_forever).start()

    def on_message(self, ws, message):
        # 받은 메시지를 session_state에 추가
        message_data = json.loads(message)
        st.session_state.messages.append(message_data)

    def on_error(self, ws, error):
        st.error(f"WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        st.warning("WebSocket connection closed")

    def on_open(self, ws):
        st.success("WebSocket connection opened")

    def send_message(self, message):
        if self.ws and self.ws.sock and self.ws.sock.connected:
            self.ws.send(json.dumps(message))
        else:
            st.error("WebSocket is not connected")
            
# Streamlit 앱 초기화
def init_app():
    if 'ws_client' not in st.session_state:
        st.session_state.ws_client = WebSocketClient(API_GATEWAY_URL)
        st.session_state.ws_client.connect()
    if 'messages' not in st.session_state:
        st.session_state.messages = []

# 메인 앱 함수
def main():
    st.title("실시간 번역 채팅 애플리케이션")

    # 사용자 정보 설정 (URL 파라미터에서 가져옴)
    query_params = st.experimental_get_query_params()
    current_user = query_params.get("user", ["default"])[0]

    # 사용자별 UI 렌더링
    if current_user == "user1":  # 한국인 사용자
        st.header("🇰🇷 한국어 채팅")
        input_lang, output_lang = "ko", "ja"
        input_placeholder = "한국어 메시지 입력"
        send_button = "전송"
    elif current_user == "user2":  # 일본인 사용자
        st.header("🇯🇵 日本語チャット")
        input_lang, output_lang = "ja", "ko"
        input_placeholder = "日本語メッセージを入力"
        send_button = "送信"
    else:
        st.error("Invalid user. Please use ?user=user1 or ?user=user2 in the URL.")
        st.stop()

    # 메시지 입력 및 전송
    with st.form(key='message_form'):
        user_input = st.text_input(input_placeholder)
        submit_button = st.form_submit_button(label=send_button)

        if submit_button and user_input:
            message = {
                "action": "sendmessage",
                "user": current_user,
                "content": user_input,
                "source_lang": input_lang,
                "target_lang": output_lang
            }
            st.session_state.ws_client.send_message(message)

    # 메시지 표시
    for msg in st.session_state.messages:
        st.text(f"{msg['user']}: {msg['content']}")

    # 주기적으로 화면 갱신
    if st.button("새로고침"):
        st.experimental_rerun()

if __name__ == "__main__":
    init_app()
    main()