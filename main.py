import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import yfinance as yf
import requests
import json

# 1. 환경변수 가져오기
EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# 받는 사람도 나, 보내는 사람도 나
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
            
            # 상승/하락에 따라 이모지 및 색상(HTML) 적용
            color = "red" if change > 0 else "blue"
            emoji = "🔺" if change > 0 else "Vk"
            data_list.append(f"<span style='color:{color}'>{emoji} {name}: {close:,.2f} ({change:+.2f}%)</span>")
        except Exception as e:
            print(f"Error fetching {name}: {e}")
            continue
    
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
        except Exception:
            continue
    
    return news_content

def generate_html_report(market_data, news_data):
    today_date = datetime.now().strftime("%Y년 %m월 %d일")
    
    prompt = f"""
    당신은 월가 전문 애널리스트입니다. 아래 데이터를 바탕으로 직장인을 위한 '미국 증시 모닝 리포트'를 작성해주세요.
    
    [필수 요청사항]
    1. **반드시 HTML 코드로만 출력하세요.** (```html 같은 마크다운 태그 없이 <html>로 시작해서 </html>로 끝나게)
    2. 디자인: 깔끔한 이메일 뉴스레터 스타일 (CSS style을 인라인으로 사용)
    3. 구성:
       - <h2>제목: {today_date} 미국 증시 요약</h2>
       - <h3>1. 시장 지수 현황</h3>: 지수 데이터를 표(Table)나 리스트로 정리하고, 상승/하락 원인을 요약.
       - <h3>2. 주요 뉴스 & 이슈</h3>: 뉴스 헤드라인을 보고 핵심 이슈 3가지를 뽑아 분석.
       - <h3>3. 제미나이의 코멘트</h3>: 현재 시장 분위기와 투자 조언 한마디.
    4. 상승은 빨간색(Red), 하락은 파란색(Blue) 텍스트로 표현.

    [시장 데이터]
    {market_data}

    [뉴스 헤드라인]
    {news_data}
    """
    
    # ✅ 여기가 핵심 수정 사항입니다! (gemini-pro -> gemini-1.5-flash)
    url = f"[https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=](https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=){GEMINI_API_KEY}"
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    data = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        
        # 결과 텍스트 추출
        if 'candidates' in result and len(result['candidates']) > 0:
            content = result['candidates'][0]['content']['parts'][0]['text']
        elif 'error' in result:
            raise Exception(f"Gemini API Error: {result['error']['message']}")
        else:
            raise Exception("Unexpected API response format")
        
        content = content.replace("```html", "").replace("```", "")
        return content
        
    except Exception as e:
        print(f"Error generating report: {e}")
        # 에러 발생 시 비상용 간단 리포트 반환
        return f"<html><body><h2>{today_date} 리포트 작성 실패</h2><p>AI 연결 중 오류가 발생했습니다: {e}</p></body></html>"

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
            
        print("이메일 발송 성공!")
    except Exception as e:
        print(f"이메일 발송 실패: {e}")

if __name__ == "__main__":
    print("데이터 수집 및 리포트 작성 중...")
    try:
        market_data = get_market_data()
        news_data = get_news_summary()
        html_report = generate_html_report(market_data, news_data)
        
        print("이메일 전송 중...")
        send_email(html_report)
    except Exception as main_e:
        print(f"치명적 오류 발생: {main_e}")
