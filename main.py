import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import yfinance as yf
import requests
import json

# 환경변수
EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
TO_EMAIL = EMAIL_USER 

def get_market_data():
    tickers = {'S&P 500': '^GSPC', 'Dow Jones': '^DJI', 'Nasdaq': '^IXIC', 'Russell 2000': '^RUT'}
    data_list = []
    for name, ticker in tickers.items():
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d")
            if len(hist) < 2: continue
            close = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2]
            change = ((close - prev_close) / prev_close) * 100
            color = "red" if change > 0 else "blue"
            emoji = "🔺" if change > 0 else "Vk"
            data_list.append(f"<span style='color:{color}'>{emoji} {name}: {close:,.2f} ({change:+.2f}%)</span>")
        except: continue
    return "<br>".join(data_list)

def get_news_summary():
    symbols = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL', 'MSFT']
    news_content = ""
    for symbol in symbols:
        try:
            stock = yf.Ticker(symbol)
            news = stock.news
            if news:
                for item in news[:1]:
                    title = item.get('title', '')
                    link = item.get('link', '')
                    news_content += f"- <b>[{symbol}]</b> <a href='{link}'>{title}</a><br>"
        except: continue
    return news_content

def call_gemini_api(prompt):
    # [전략] v1 정식 버전의 gemini-pro를 최우선으로 시도합니다.
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        if 'candidates' in result:
            return result['candidates'][0]['content']['parts'][0]['text']
        else:
            print(f"AI 응답 실패: {result}")
            return None
    except Exception as e:
        print(f"AI 연결 에러: {e}")
        return None

def generate_html_report(market_data, news_data):
    today_date = datetime.now().strftime("%Y년 %m월 %d일")
    
    prompt = f"""
    당신은 월가 전문 애널리스트입니다. 아래 데이터를 바탕으로 직장인을 위한 '미국 증시 모닝 리포트'를 HTML로 작성해주세요.
    
    [필수]
    1. 결과는 오직 HTML 코드만 출력. (```html 태그 금지)
    2. 디자인: 깔끔한 이메일 뉴스레터 스타일.
    3. 내용:
       - <h2>제목: {today_date} 미국 증시 요약</h2>
       - <h3>1. 시장 현황</h3>: 지수 등락과 원인 1줄 요약.
       - <h3>2. 주요 뉴스</h3>: 핵심 이슈 3가지 요약.
       - <h3>3. 오선의 코멘트</h3>: 투자 조언.
    4. 상승(Red), 하락(Blue).

    [데이터]
    {market_data}
    
    [뉴스]
    {news_data}
    """
    
    # 1. AI에게 요약 요청
    ai_content = call_gemini_api(prompt)
    
    # 2. 성공하면 AI 내용 반환
    if ai_content:
        return ai_content.replace("```html", "").replace("```", "")
    
    # 3. 실패하면 '안전장치' 발동: 수집한 데이터라도 예쁘게 보여줌
    return f"""
    <html>
    <body>
        <h2>🇺🇸 {today_date} 미국 증시 속보 (AI 미작동)</h2>
        <p>※ AI 연결에 일시적 문제가 있어 원본 데이터를 전송합니다.</p>
        <hr>
        <h3>📊 시장 지수</h3>
        <p>{market_data}</p>
        <hr>
        <h3>📰 주요 뉴스 헤드라인</h3>
        <p>{news_data}</p>
    </body>
    </html>
    """

def send_email(html_content):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = TO_EMAIL
        msg['Subject'] = f"🇺🇸 [모닝 리포트] {datetime.now().strftime('%m월 %d일')} 미국 증시 시황"
        msg.attach(MIMEText(html_content, 'html'))
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
    except: pass

if __name__ == "__main__":
    m_data = get_market_data()
    n_data = get_news_summary()
    final_report = generate_html_report(m_data, n_data)
    send_email(final_report)
