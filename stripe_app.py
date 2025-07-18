# stripe_app.py
# ----------------------------------------------------------
# このアプリは、Microsoft Copilotの助言と設計支援を元に構築しました。
# グレースケール画像をストライプ状のSVGへ変換するWebツールです。
# オープンソースとして公開しており、改良・派生を歓迎します。
#
# Created by Origami_Gyokuo - 2025
# Repository: https://github.com/gyokuo1007/grayscale-stripe-svg
# License: MIT
# ----------------------------------------------------------

from PIL import Image
from io import BytesIO
import numpy as np
import xml.etree.ElementTree as ET
from xml.dom import minidom
import streamlit as st
import streamlit.components.v1 as components

def read_image_from_bytes(file_bytes):
    image = Image.open(BytesIO(file_bytes)).convert("L")
    return np.array(image)

def resize_image(img_array, new_size):
    image = Image.fromarray(img_array)
    resized = image.resize(new_size, Image.Resampling.BOX)
    return np.array(resized)

def create_stripe_svg(img, block_size=12, max_lines=5, line_spacing=1, merge_threshold=1, combine_path=False):
    h, w = img.shape
    svg = ET.Element("svg", xmlns="http://www.w3.org/2000/svg", version="1.1",
                     width="100%", height="auto", viewBox=f"0 0 {w} {h}",
                     preserveAspectRatio="xMidYMid meet")
    line_buffer = {}

    for by in range(0, h, block_size):
        for bx in range(0, w, block_size):
            block = img[by:by + block_size, bx:bx + block_size]
            if block.size == 0:
                continue
            avg = np.mean(block)
            density = int(((255 - avg) / 255) * max_lines)
            for i in range(density):
                y = by + i * line_spacing
                if y >= by + block_size:
                    break
                line_buffer.setdefault(y, []).append((bx, bx + block_size))

    def merge_segments(segments):
        merged = []
        for x1, x2 in sorted(segments):
            if not merged or x1 > merged[-1][1] + merge_threshold:
                merged.append([x1, x2])
            else:
                merged[-1][1] = max(merged[-1][1], x2)
        return merged

    if combine_path:
        path_data = []
        for y in sorted(line_buffer.keys()):
            for x1, x2 in merge_segments(line_buffer[y]):
                path_data.append(f"M {x1} {y} L {x2} {y}")
        if path_data:
            ET.SubElement(svg, "path", {
                "d": " ".join(path_data),
                "stroke": "black",
                "stroke-width": "0.5",
                "fill": "none"
            })
    else:
        for y in sorted(line_buffer.keys()):
            for x1, x2 in merge_segments(line_buffer[y]):
                ET.SubElement(svg, "line", {
                    "x1": str(x1),
                    "y1": str(y),
                    "x2": str(x2),
                    "y2": str(y),
                    "stroke": "black",
                    "stroke-width": "0.5"
                })

    return minidom.parseString(ET.tostring(svg, 'utf-8')).toprettyxml(indent="  ")

# Streamlit UI
st.set_page_config(page_title="Linear Halftone SVG Generator", layout="wide")
st.title("線形ハーフトーン変換ツール")

uploaded_file = st.file_uploader("画像をアップロード（.jpg, .png, .bmp）", type=["jpg", "png", "bmp"])
if uploaded_file:
    img = read_image_from_bytes(uploaded_file.read())
    h_px, w_px = img.shape
    img_ratio = w_px / h_px

    st.subheader("サイズ設定")
    lock_aspect = st.checkbox("縦横比を維持", value=True)
    combine_path = st.checkbox("パスを結合", value=True)
    target_w = st.number_input("幅 (px)", min_value=50, max_value=5000, value=w_px)
    target_h = st.number_input("高さ (px)", min_value=50, max_value=5000, value=h_px)

    if lock_aspect:
        ratio_mode = st.radio("比率維持の基準", ["幅を基準に調整", "高さを基準に調整"], index=0)
        if ratio_mode == "幅を基準に調整":
            new_w = int(target_w)
            new_h = int(round(target_w / img_ratio))
        else:
            new_h = int(target_h)
            new_w = int(round(target_h * img_ratio))
    else:
        new_w = int(target_w)
        new_h = int(target_h)

    st.caption(f"実際の処理サイズ： {new_w}px × {new_h}px")
    resized = resize_image(img, (new_w, new_h))
    svg_code = create_stripe_svg(resized, combine_path=combine_path)

    st.subheader("SVG プレビュー")

    # 左寄せ・余白統一のSVG表示
    svg_html = f"""
    <div style="text-align:left; background:white; margin-top:16px; margin-bottom:24px;">
      <div style="display:inline-block; max-width:100%; height:auto;">
        {svg_code}
      </div>
    </div>
    """
    components.html(svg_html, height=600)

    # 上下の余白をSVGと同様に揃える
    st.markdown("<div style='margin-bottom:24px;'>", unsafe_allow_html=True)
    st.success("ストライプSVG生成完了", icon="✅")
    st.markdown("</div>", unsafe_allow_html=True)

    st.download_button("SVGをダウンロード", svg_code.encode("utf-8"),
                       file_name="stripe_output.svg", mime="image/svg+xml")
    st.code(svg_code, language="xml")