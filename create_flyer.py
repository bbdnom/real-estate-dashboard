#!/usr/bin/env python3
"""방배동 도심복합사업 시즌2 — 주민 설득용 1장 전단지 (v4 컴팩트)"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import qrcode, io

pdfmetrics.registerFont(TTFont('B', '/tmp/NanumGothicBold.ttf'))
pdfmetrics.registerFont(TTFont('R', '/tmp/NanumGothicRegular.ttf'))

BK = HexColor('#1A1A1A')
DK = HexColor('#333333')
MD = HexColor('#666666')
LT = HexColor('#999999')
BG = HexColor('#F2F2F2')
WH = white
RD = HexColor('#C62828')

W, H = A4
out = '/home/hemannkim/real-estate-dashboard/방배동_도심복합사업_안내.pdf'
c = canvas.Canvas(out, pagesize=A4)
tw = W - 30*mm  # 본문 너비

# ════════ 상단 타이틀 ════════
y = H - 14*mm
c.setFillColor(BK)
c.setFont('B', 28)
c.drawCentredString(W/2, y, '방배동 도심복합사업 시즌2')

y -= 10*mm
c.setStrokeColor(RD); c.setLineWidth(2)
c.line(15*mm, y, W - 15*mm, y)

y -= 8*mm
c.setFillColor(DK); c.setFont('R', 11)
c.drawCentredString(W/2, y, '서울 서초구 방배동 474~980번지 일대  |  사당역 도보 5분')

y -= 8*mm
c.setFillColor(RD); c.setFont('B', 14)
c.drawCentredString(W/2, y, '참여의향서 접수 중  |  마감: 5월 8일(목)')

y -= 7*mm
c.setFillColor(MD); c.setFont('R', 9.5)
c.drawCentredString(W/2, y, '⚠️ 전국에서 도심공공 신청 급증 — 모아타운·신속통합기획 지역도 시즌2로 전환 중, 경쟁 치열')

# ════════ 지도 + 구역 현황 ════════
y -= 12*mm
map_h = 44*mm
map_w = 68*mm

try:
    c.drawImage(ImageReader('/home/hemannkim/real-estate-dashboard/방배2동.png'),
                15*mm, y - map_h, map_w, map_h, preserveAspectRatio=True, anchor='nw')
except:
    c.setFillColor(BG)
    c.rect(15*mm, y - map_h, map_w, map_h, fill=1)

ix = 15*mm + map_w + 8*mm
c.setFillColor(BK); c.setFont('B', 13)
c.drawString(ix, y - 6*mm, '구역 현황')
c.setFont('R', 11); c.setFillColor(DK)
for i, t in enumerate(['사당역 2·4호선 도보 5분',
                        '방배15구역(포스코이앤씨) 인접',
                        '사당복합환승센터 추진 중',
                        '1군 건설사 브랜드 아파트로 전환']):
    c.drawString(ix, y - 17*mm - i*9.5*mm, f'• {t}')

# ════════ 비교표 ════════
y -= map_h + 8*mm
c.setFillColor(BK); c.setFont('B', 15)
c.drawString(15*mm, y, '"공공사업이라 싫은데요?"')
y -= 6*mm
c.setFillColor(RD); c.setFont('B', 11)
c.drawString(15*mm, y, '시즌2는 이전과 완전히 다릅니다.')

y -= 7*mm
col1, col2, col3 = 40*mm, 55*mm, 55*mm
rh = 10*mm

# 헤더
c.setFillColor(BK)
c.rect(15*mm, y - rh, tw, rh, fill=1, stroke=0)
c.setFillColor(WH); c.setFont('B', 10.5)
c.drawCentredString(15*mm + col1/2, y - 7*mm, '항목')
c.drawCentredString(15*mm + col1 + col2/2, y - 7*mm, '일반 공공재개발')
c.drawCentredString(15*mm + col1 + col2 + col3/2, y - 7*mm, '★ 시즌2')

rows = [('아파트 브랜드', 'LH 공공아파트', '삼성·DL 등 1군 브랜드'),
        ('분양가 상한제', '적용 (싸게 분양)', '미적용 (시세대로)'),
        ('개발이익', 'LH와 배분', '전액 주민 환원'),
        ('사업 기간', '10년 이상', '3~5년 패스트트랙')]

for i, (a, b, d) in enumerate(rows):
    ry = y - rh - i*rh
    c.setFillColor(BG if i % 2 == 0 else WH)
    c.rect(15*mm, ry - rh, tw, rh, fill=1, stroke=0)
    c.setFillColor(BK); c.setFont('B', 10)
    c.drawCentredString(15*mm + col1/2, ry - 7*mm, a)
    c.setFillColor(LT); c.setFont('R', 10)
    c.drawCentredString(15*mm + col1 + col2/2, ry - 7*mm, b)
    c.setFillColor(RD); c.setFont('B', 10)
    c.drawCentredString(15*mm + col1 + col2 + col3/2, ry - 7*mm, d)

c.setStrokeColor(HexColor('#DDD'))
c.rect(15*mm, y - rh - len(rows)*rh, tw, rh*(len(rows)+1), fill=0, stroke=1)
y = y - rh - len(rows)*rh

# ════════ 반박 2개 (한 줄씩) ════════
y -= 7*mm
c.setFillColor(BG)
c.roundRect(15*mm, y - 17*mm, tw, 17*mm, 2*mm, fill=1, stroke=0)
c.setFillColor(BK); c.setFont('B', 12)
c.drawString(20*mm, y - 6*mm, '⏩  "살아 있는 동안 안 될 거다?"')
c.setFillColor(DK); c.setFont('R', 10)
c.drawString(20*mm, y - 15*mm, '통합심의 패스트트랙 → 선정~입주 3~5년. 민간 재개발(10년+)과 다릅니다.')

y -= 23*mm
c.setFillColor(BG)
c.roundRect(15*mm, y - 17*mm, tw, 17*mm, 2*mm, fill=1, stroke=0)
c.setFillColor(BK); c.setFont('B', 12)
c.drawString(20*mm, y - 6*mm, '🏗️  공공이어서 오히려 가능한 것들')
c.setFillColor(DK); c.setFont('R', 10)
c.drawString(20*mm, y - 15*mm, '대로변 상가빌딩 현금청산, 용적률 1.4배, 인허가 통합심의 — 민간은 불가.')

# ════════ 하단 검정 영역: 참여방법 + QR + 연락처 ════════
bottom_h = 55*mm
c.setFillColor(BK)
c.rect(0, 0, W, bottom_h, fill=1, stroke=0)

# QR
qr = qrcode.QRCode(version=1, box_size=10, border=1)
qr.add_data('https://open.kakao.com/o/pbsLrLoi')
qr.make(fit=True)
qr_img = qr.make_image(fill_color='white', back_color='#1A1A1A')
buf = io.BytesIO(); qr_img.save(buf, format='PNG'); buf.seek(0)

qr_s = 30*mm
c.drawImage(ImageReader(buf), 15*mm, 14*mm, qr_s, qr_s)
c.setFillColor(LT); c.setFont('R', 8)
c.drawCentredString(15*mm + qr_s/2, 9*mm, '▲ 카카오 오픈채팅')

# 오른쪽
ix = 52*mm
c.setFillColor(WH); c.setFont('B', 14)
c.drawString(ix, 43*mm, '참여 방법')

c.setFont('R', 11.5); c.setFillColor(HexColor('#CCCCCC'))
c.drawString(ix, 33*mm, '① QR코드 촬영 → 카카오 오픈채팅 참여')
c.drawString(ix, 23*mm, '② 참여의향서 작성 (현장 또는 우편)')
c.drawString(ix, 13*mm, '③ 신분증 사본 제출 (주민등록증/면허증)')

c.setFillColor(WH); c.setFont('B', 9.5)
c.drawString(ix, 5*mm, '대표 김혜만 (제네시스빌 401호)  |  cafe.naver.com/bangbae980')

# 마감 강조 바
c.setFillColor(RD)
c.rect(0, 0, W, 8*mm, fill=1, stroke=0)
c.setFillColor(WH); c.setFont('B', 11)
c.drawCentredString(W/2, 2*mm, '마감: 5월 8일 — 놓치면 다음 기회는 없습니다')

c.save()
print(f'PDF 생성 완료: {out}')
