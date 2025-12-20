import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import yfinance as yf
import requests
import json
import time

# 1. 환경변수 설정
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
                    news_content += f"- [{symbol}] <a href='{link}'>{title}</a><br>"
        except: continue
    return news_content

def try_generate_content(prompt):
    # 사용 가능한 모델들을 순서대로 시도 (하나라도 걸려라 전략)
    models_to_try = [
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-pro",
        "gemini-1.0-pro"
    ]
    
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    last_error = ""
    
    for model in models_to_try:
        print(f"모델 시도 중: {model}...")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        
        try:
            response = requests.post(url, headers=headers, json=data)
            result = response.json()
            
            # 성공 케이스
            if 'candidates' in result:
                return result['candidates'][0]['content']['parts'][0]['text']
            
            # 실패 케이스 (다음 모델 시도)
            if 'error' in result:
                last_error = result['error'].get('message', 'Unknown Error')
                print(f"실패 ({model}): {last_error}")
                continue
                
        except Exception as e:
            print(f"연결 오류 ({model}): {e}")
            last_error = str(e)
            continue
            
    # 모든 모델이 실패했을 경우
    raise Exception(f"모든 모델 시도 실패. 마지막 오류: {last_error}")

def generate_html_report(market_data, news_data):
    today_date = datetime.now().strftime("%Y년 %m월 %d일")
    
    prompt = f"""
    당신은 월가 전문 애널리스트입니다. 아래 데이터를 바탕으로 직장인을 위한 '미국 증시 모닝 리포트'를 HTML로 작성해주세요.
    Design: 깔끔한 이메일 뉴스레터 스타일 (인라인 CSS).
    Content:
    1. 제목: {today_date} 미국 증시 요약
    2. 시장 지수 현황 (표/리스트)
    3. 주요 뉴스 & 이슈 (핵심 3가지)
    4. 제미나이 코멘트
    Style: 상승(Red), 하락(Blue).
    Output: Only HTML code. No markdown tags.

    [Market Data]
    {market_data}

    [News]
    {news_data}
    """
    
    try:
        content = try_generate_content(prompt)
        return content.replace("```html", "").replace("```", "")
    except Exception as e:
        return f"<html><body><h2>리포트 생성 실패</h2><p>{e}</p></body></html>"

def send_email(html_content):
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = TO_EMAIL
        msg['Subject'] = f"🇺🇸 [제미나이 모닝 리포트] {datetime.now().strftime('%m월 %d일')} 미국 증시 시황"
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
