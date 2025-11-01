import streamlit as st
import io
import base64
import asyncio
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from agent import Y2DocAgent

def generate_pdf(transcript_text: str) -> bytes:
    """
    將轉錄文字轉成 PDF 二進位內容（bytes）
    """
    buffer = io.BytesIO()
    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))  # 支援中文
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("HeiseiKakuGo-W5", 12)
    margin_x, margin_y = 50, 780
    line_height = 18  # 行距

    c.drawString(margin_x, height - 40, "🎬 YouTube Transcript:")

    text_obj = c.beginText(margin_x, margin_y)
    text_obj.setLeading(line_height)

    # 自動分行
    import textwrap
    for line in textwrap.wrap(transcript_text, width=90):
        text_obj.textLine(line)
        if text_obj.getY() < 50:
            c.drawText(text_obj)
            c.showPage()
            c.setFont("HeiseiKakuGo-W5", 12)
            text_obj = c.beginText(margin_x, height - 50)
            text_obj.setLeading(line_height)

    c.drawText(text_obj)
    c.save()
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data

async def main():
    st.set_page_config(page_title="🎧 YouTube 語音轉文字", layout="centered")
    st.title("🎧 YouTube 語音轉文字 Agent")
    st.caption("使用 Whisper 模型進行轉錄，並回傳 Base64 編碼結果。")

    if "transcript" not in st.session_state:
        st.session_state.transcript = ""

    # agent
    aiagent_client = Y2DocAgent()
    agent = aiagent_client.create_agent()

    # enter url
    youtube_url = st.text_input("請輸入 YouTube 影片網址：")

    download_fmt = st.selectbox("下載格式", ["TXT", "PDF"], index=0)

    if st.button("開始轉錄"):
        if not youtube_url:
            st.warning("⚠️ 請輸入 YouTube 網址。")
        else:
            with st.spinner("⏳ 處理中，請稍候..."):
                try:
                    result = agent.invoke({"youtube_url": youtube_url})
                    st.session_state.transcript = result["transcript_text"]

                    st.success("✅ 轉錄完成！")
                    st.subheader("📝 轉錄內容")
                    st.text_area("轉錄結果：", st.session_state.transcript, height=300)

                    st.subheader("📥 下載")
                    if download_fmt == "TXT":
                        txt_bytes = st.session_state.transcript.encode("utf-8")
                        st.download_button(
                            label="📄 下載 TXT",
                            data=txt_bytes,
                            file_name="transcript.txt",
                            mime="text/plain",
                        )
                    else:
                        pdf_bytes = generate_pdf(st.session_state.transcript)
                        st.download_button(
                            label="📘 下載 PDF",
                            data=pdf_bytes,
                            file_name="transcript.pdf",
                            mime="application/pdf",
                        )

                except Exception as e:
                    st.error(f"❌ 發生錯誤：{e}")


if __name__ == "__main__":
    asyncio.run(main())