import os
import base64
import asyncio
import whisper
import yt_dlp
import textwrap
from dotenv import load_dotenv
from typing import TypedDict
from langgraph.graph import StateGraph, START, END

# # 英文字體 (內建)
# EN_FONT = "Times-Roman"
# # 中文字體 (ReportLab CIDFont)
# CN_FONT = "HeiseiKakuGo-W5"
# # 字型大小與行距
# FONT_SIZE = 12
# LINE_SPACING = 18
# # 每行最大字數（越小越換行）
# MAX_CHARS_PER_LINE = 90

# === 
# base function
# ===
def load_or_download_whisper(model_name: str = "base", model_dir: str = "models"):
    """
    若 models/ 內已有指定模型，則直接載入；
    若沒有則自動下載到 models/ 資料夾。
    """
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, f"{model_name}.pt")

    if os.path.exists(model_path):
        print(f"偵測到現有模型：{model_path}")
    else:
        print(f"模型 {model_name} 不存在，開始下載到 {model_dir}...")
    model = whisper.load_model(model_name, download_root=model_dir)
    print(f"Whisper 模型載入完成")
    return model

class VideoState(TypedDict):
    youtube_url: str
    audio_path: str
    transcript_text: str
    file_base64: str

class Y2DocAgent:
    def __init__(self):
        pass

    def create_agent(self):
        # ===
        # node function
        # ===
        def download_audio_node(state: VideoState) -> VideoState:
            print("使用 yt-dlp 下載 YouTube 音訊中...")
            url = state["youtube_url"]
            output_dir = "downloads"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, "%(title)s.%(ext)s")

            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": output_path,
                "quiet": True,
                "noplaylist": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info).rsplit(".", 1)[0] + ".mp3"

            print(f"音訊下載完成：{filename}")
            state["audio_path"] = filename
            return state
        
        def transcribe_audio_node(state: VideoState) -> VideoState:
            print("載入 Whisper 模型並開始語音轉文字...")
            model = load_or_download_whisper("base", "models")
            result = model.transcribe(state["audio_path"])
            state["transcript_text"] = result["text"]
            print("語音轉文字完成。")
            return state
        
        def prepare_output_node(state: VideoState) -> VideoState:
            text = state["transcript_text"]
            encoded_bytes = base64.b64encode(text.encode("utf-8"))
            state["file_base64"] = encoded_bytes.decode("utf-8")
            print("已生成 Base64 編碼，可直接回傳前端。")

            # 刪除音訊暫存檔，避免 downloads 資料夾爆滿
            try:
                if os.path.exists(state["audio_path"]):
                    os.remove(state["audio_path"])
                    print(f"🧹 已刪除暫存音訊檔：{state['audio_path']}")
            except Exception as e:
                print(f"刪除音訊檔失敗：{e}")

            return state

        # def generate_file_node(state: VideoState) -> VideoState:
        #     text = state["transcript_text"]
        #     fmt = state.get("output_format", "pdf").lower()
        #     os.makedirs("outputs", exist_ok=True)

        #     if fmt == "txt":
        #         output_path = os.path.join("outputs", "transcript.txt")
        #         with open(output_path, "w", encoding="utf-8") as f:
        #             f.write(text)
        #         print(f"TXT 檔案已產生：{output_path}")

        #     else:
        #         output_path = os.path.join("outputs", "transcript.pdf")

        #         # 註冊中文字體
        #         pdfmetrics.registerFont(UnicodeCIDFont(CN_FONT))

        #         c = canvas.Canvas(output_path, pagesize=A4)
        #         width, height = A4
        #         margin_x, margin_y = 50, 780

        #         c.setFont(CN_FONT, FONT_SIZE)

        #         c.drawString(margin_x, height - 40, "🎬 YouTube Transcript:")
        #         text_obj = c.beginText(margin_x, margin_y)
        #         text_obj.setLeading(LINE_SPACING)

        #         wrapped_lines = textwrap.wrap(text, width=MAX_CHARS_PER_LINE)

        #         for line in wrapped_lines:
        #             if line.isascii():
        #                 c.setFont(EN_FONT, FONT_SIZE)
        #             else:
        #                 c.setFont(CN_FONT, FONT_SIZE)
        #             text_obj.textLine(line)
        #             if text_obj.getY() < 50:  # 到頁底自動換頁
        #                 c.drawText(text_obj)
        #                 c.showPage()
        #                 c.setFont(CN_FONT, FONT_SIZE)
        #                 text_obj = c.beginText(margin_x, height - 50)
        #                 text_obj.setLeading(LINE_SPACING)

        #         c.drawText(text_obj)
        #         c.save()
        #         print(f"PDF 檔案已產生：{output_path}")

        #     state["output_path"] = output_path

        #     # 將輸出檔案轉為 base64 編碼字串
        #     with open(output_path, "rb") as f:
        #         encoded_bytes = base64.b64encode(f.read())
        #         state["file_base64"] = encoded_bytes.decode("utf-8")

        #     return state
        
        # ===
        # Build graph
        # ===
        builder = StateGraph(VideoState)
        builder.add_node("download_audio", download_audio_node)
        builder.add_node("transcribe_audio", transcribe_audio_node)
        builder.add_node("prepare_output_node", prepare_output_node)

        builder.add_edge(START, "download_audio")
        builder.add_edge("download_audio", "transcribe_audio")
        builder.add_edge("transcribe_audio", "prepare_output_node")
        builder.add_edge("prepare_output_node", END)

        agent = builder.compile()

        return agent

async def main():
    aiagent_client = Y2DocAgent()
    agent = aiagent_client.create_agent()

    youtube_url = input("Enter YouTube URL: ")
    init_params = {
        "youtube_url": youtube_url
    }
    result = agent.invoke(input=init_params)
    print("\n🎉 完成！")
    print("轉錄文字：")
    print(result["transcript_text"][:300] + "..." if len(result["transcript_text"]) > 300 else result["transcript_text"])
    print("\nBase64 前 100 字：", result["file_base64"][:100])


if __name__ == "__main__":
    asyncio.run(main())