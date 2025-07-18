# stripe_app.py
# ----------------------------------------------------------
# このアプリは、Microsoft Copilotの助言と設計支援を元に構築しました。
# 画像をグレースケールストライプ状のSVGへ変換するWebツールです。
# オープンソースとして公開しており、改良・派生を歓迎します。
#
# Created by Origami_Gyokuo - 2025
# Repository: https://github.com/gyokuo1007/grayscale-stripe-svg
# License: MIT
# ----------------------------------------------------------

from PIL import Image, ExifTags, ImageOps
from io import BytesIO
import numpy as np
import xml.etree.ElementTree as ET
from xml.dom import minidom
import streamlit as st
import streamlit.components.v1 as components
import os

def read_image_from_bytes(file_bytes, mode="モノクロ"):
    image = Image.open(BytesIO(file_bytes))
    try:
        exif = image._getexif()
        if exif:
            orientation_key = next(k for k, v in ExifTags.TAGS.items() if v == 'Orientation')
            if orientation_key in exif:
                image = ImageOps.exif_transpose(image)
    except Exception:
        pass

    if mode == "モノクロ":
        return np.array(image.convert("L"))
    else:
        return np.array(image.convert("RGB"))

def resize_image(img_array, new_size):
    image = Image.fromarray(img_array)
    resized = image.resize(new_size, Image.Resampling.BOX)
    return np.array(resized)

def build_svg_tree(img, w, h, direction, mode, block_size=12, max_lines=5, line_spacing=1, merge_threshold=1,
                   use_absolute_size=False):
    svg_attrib = {
        "xmlns": "http://www.w3.org/2000/svg",
        "version": "1.1"
    }

    if use_absolute_size:
        svg_attrib["width"] = f"{w}px"
        svg_attrib["height"] = f"{h}px"
    else:
        svg_attrib["width"] = "100%"
        svg_attrib["height"] = "auto"
        svg_attrib["viewBox"] = f"0 0 {w} {h}"
        svg_attrib["preserveAspectRatio"] = "xMidYMid meet"

    svg = ET.Element("svg", svg_attrib)
    line_buffer = {}

    is_color = mode == "カラー"

    for by in range(0, h, block_size):
        for bx in range(0, w, block_size):
            block = img[by:by + block_size, bx:bx + block_size]
            if block.size == 0:
                continue

            # 密度と色の計算
            if is_color:
                avg_color = np.mean(block.reshape(-1, 3), axis=0)
                stroke_color = "#{:02x}{:02x}{:02x}".format(*avg_color.astype(int))
                gray = int(np.dot(avg_color, [0.2989, 0.5870, 0.1140]))  # 手動で輝度換算
                density = int(((255 - gray) / 255) * max_lines)
            else:
                avg = np.mean(block)
                density = int(((255 - avg) / 255) * max_lines)
                stroke_color = "black"

            for i in range(density):
                if direction == "水平":
                    y = by + i * line_spacing
                    if y >= by + block_size:
                        break
                    line_buffer.setdefault(y, []).append((bx, bx + block_size, stroke_color))
                elif direction == "垂直":
                    x = bx + i * line_spacing
                    if x >= bx + block_size:
                        break
                    line_buffer.setdefault(x, []).append((by, by + block_size, stroke_color))

    def merge_segments(segments):
        merged = []
        for x1, x2, color in sorted(segments):
            if not merged or x1 > merged[-1][1] + merge_threshold or color != merged[-1][2]:
                merged.append([x1, x2, color])
            else:
                merged[-1][1] = max(merged[-1][1], x2)
        return merged

    for key in sorted(line_buffer.keys()):
        for x1, x2, color in merge_segments(line_buffer[key]):
            if direction == "水平":
                ET.SubElement(svg, "path", {
                    "d": f"M {x1} {key} L {x2} {key}",
                    "stroke": color,
                    "stroke-width": "0.5",
                    "fill": "none"
                })
            elif direction == "垂直":
                ET.SubElement(svg, "path", {
                    "d": f"M {key} {x1} L {key} {x2}",
                    "stroke": color,
                    "stroke-width": "0.5",
                    "fill": "none"
                })

    return minidom.parseString(ET.tostring(svg, 'utf-8')).toprettyxml(indent="  ")

# Streamlit UI
st.set_page_config(page_title="Linear Halftone SVG Generator", layout="wide")
st.title("線形ハーフトーン変換ツール")

uploaded_file = st.file_uploader("画像をアップロード（.jpg, .png, .bmp）", type=["jpg", "png", "bmp"])
if uploaded_file:
    st.subheader("ストライプモードの選択")
    mode = st.radio("処理モード", ["モノクロ", "カラー"])

    raw_img = read_image_from_bytes(uploaded_file.read(), mode=mode)
    h_px, w_px = raw_img.shape[:2]
    img_ratio = w_px / h_px

    # 最大5000pxで制限
    w_px = min(w_px, 5000)
    h_px = min(h_px, 5000)

    st.subheader("線の向き")
    direction = st.selectbox("線の向きを選択", ["水平", "垂直"])

    st.subheader("サイズ設定")
    lock_aspect = st.checkbox("縦横比を維持", value=True)
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
    resized = resize_image(raw_img, (new_w, new_h))

    svg_for_display = build_svg_tree(resized, new_w, new_h, direction, mode, use_absolute_size=False)
    svg_for_download = build_svg_tree(resized, new_w, new_h, direction, mode, use_absolute_size=True)

    st.subheader("SVG プレビュー")
    svg_html = f"""
    <div style="text-align:left; background:white; margin-top:16px; margin-bottom:24px;">
      <div style="display:inline-block; max-width:100%; height:auto;">
        {svg_for_display}
      </div>
    </div>
    """
    components.html(svg_html, height=600)

    base_name = os.path.splitext(uploaded_file.name)[0]
    output_file_name = f"{base_name}_stripe.svg"

    st.download_button("SVGをダウンロード", svg_for_download.encode("utf-8"),
                       file_name=output_file_name, mime="image/svg+xml")
    st.code(svg_for_display, language="xml")