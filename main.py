import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import yfinance as yf
import requests
import xml.etree.ElementTree as ET

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
            # 구글 뉴스 RSS (무조건 데이터 나옴)
            url = f"https://news.google.com/rss/search?q={symbol}+stock&hl=en-US&gl=US&ceid=US:en"
            resp = requests.get(url, timeout=5)
            root = ET.fromstring(resp.content)
            item = root.find(".//item") 
            
            if item is not None:
                title = item.find("title").text
                link = item.find("link").text
                news_content += f"- <b>[{symbol}]</b> <a href='{link}'>{title}</a><br>"
        except:
            continue
            
    return news_content

def call_gemini_api(prompt):
    # ✅ 핵심 수정: 3가지 주소를 순서대로 시도합니다. (하나라도 걸려라!)
    endpoints = [
        # 1. 최신 모델 (Flash)
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}",
        # 2. 안정적인 모델 (Pro - v1beta)
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}",
        # 3. 구형 정식 모델 (Pro - v1 정식버전)
        f"https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key={GEMINI_API_KEY}"
    ]
    
    headers = {'Content-Type': 'application/json'}
    data = {"contents": [{"parts": [{"text": prompt}]}]}
    
    for url in endpoints:
        try:
            print(f"AI 연결 시도 중: {url.split('/models/')[1].split(':')[0]}...")
            response = requests.post(url, headers=headers, json=data)
            result = response.json()
            
            if 'candidates' in result:
                # 성공하면 바로 결과 반환!
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                print(f"실패: {result}")
        except Exception as e:
            print(f"에러: {e}")
            continue
            
    return None # 3개 다 실패하면 None 반환

def generate_html_report(market_data, news_data):
    today_date = datetime.now().strftime("%Y년 %m월 %d일")
    
    # ✅ 요청사항 반영: 한글 번역 + 주가 영향 분석 요청
    prompt = f"""
    You are a professional stock analyst for Korean investors.
    Analyze the US stock market data and news provided below.

    [Output Requirements]
    1. **Language:** MUST be written in **Korean (한국어)**.
    2. **Format:** HTML code only. (Clean email style).
    3. **Content Structure:**
       - <h2>제목: {today_date} 미국 증시 요약</h2>
       - <h3>1. 시장 지수 브리핑</h3>: Summarize market indices and why they moved.
       - <h3>2. 주요 뉴스 및 영향성 분석</h3>:
         - Translate the news headlines to Korean.
         - **Crucial:** Explain how this news affects the stock price (Bullish/Bearish).
       - <h3>3. 투자자 코멘트</h3>: One sentence advice.
    4. **Style:** Use Red color for Bullish/Up, Blue color for Bearish/Down.

    [Market Data]
    {market_data}
    
    [News Headlines (English)]
    {news_data}
    """
    
    ai_content = call_gemini_api(prompt)
    
    if ai_content:
        return ai_content.replace("```html", "").replace("```", "")
    
    # 실패 시 보내는 비상용 메일 (이게 오면 안 됨!)
    return f"""
    <html>
    <body>
        <h2>⚠ {today_date} AI 연결 최종 실패</h2>
        <p>죄송합니다. 3가지 모델을 모두 시도했으나 연결되지 않았습니다.</p>
        <p>API 키가 올바른지, 혹은 구글 클라우드 설정 문제가 아닌지 확인이 필요합니다.</p>
        <hr>
        <h3>수집된 뉴스 데이터 (원본)</h3>
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
