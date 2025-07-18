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
import os
os.environ['LD_LIBRARY_PATH'] = '/usr/lib/x86_64-linux-gnu'
import cv2
import numpy as np
import xml.etree.ElementTree as ET
from xml.dom import minidom
import streamlit as st

def read_image_from_bytes(file_bytes):
    img_array = np.frombuffer(file_bytes, np.uint8)
    return cv2.imdecode(img_array, cv2.IMREAD_GRAYSCALE)

def create_stripe_svg(img, block_size=12, max_lines=5, line_spacing=1, merge_threshold=1, combine_path=False):
    h, w = img.shape
    svg = ET.Element("svg", xmlns="http://www.w3.org/2000/svg", version="1.1",
                     width=f"{w}px", height=f"{h}px")

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

    if combine_path:
        path_data = []
        for y in sorted(line_buffer.keys()):
            segments = sorted(line_buffer[y])
            merged = []
            for x1, x2 in segments:
                if not merged or x1 > merged[-1][1] + merge_threshold:
                    merged.append([x1, x2])
                else:
                    merged[-1][1] = max(merged[-1][1], x2)
            for x1, x2 in merged:
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
            segments = sorted(line_buffer[y])
            merged = []
            for x1, x2 in segments:
                if not merged or x1 > merged[-1][1] + merge_threshold:
                    merged.append([x1, x2])
                else:
                    merged[-1][1] = max(merged[-1][1], x2)

            for x1, x2 in merged:
                ET.SubElement(svg, "line", {
                    "x1": str(x1),
                    "y1": str(y),
                    "x2": str(x2),
                    "y2": str(y),
                    "stroke": "black",
                    "stroke-width": "0.5"
                })

    return minidom.parseString(ET.tostring(svg, 'utf-8')).toprettyxml(indent="  ")

# 🎨 Streamlit UI
st.title("🎞️ グレースケール → ストライプSVGジェネレータ")

uploaded_file = st.file_uploader("画像をアップロード（.jpg, .png, .bmp）", type=["jpg", "png", "bmp"])
lock_aspect = st.checkbox("縦横比を維持", value=True)
combine_path = st.checkbox("パスを結合", value=True)

if uploaded_file:
    img = read_image_from_bytes(uploaded_file.read())
    h_px, w_px = img.shape
    img_ratio = w_px / h_px

    target_w = st.number_input("幅 (px)", min_value=50, max_value=5000, value=w_px)
    target_h = st.number_input("高さ (px)", min_value=50, max_value=5000, value=h_px)

    if lock_aspect:
        target_ratio = target_w / target_h
        if img_ratio > target_ratio:
            new_w = int(target_w)
            new_h = int(target_w / img_ratio)
        else:
            new_h = int(target_h)
            new_w = int(target_h * img_ratio)
    else:
        new_w = int(target_w)
        new_h = int(target_h)

    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    svg_code = create_stripe_svg(resized, combine_path=combine_path)

    st.success("✅ ストライプSVG生成完了！")
    st.download_button("SVGをダウンロード", svg_code.encode("utf-8"), file_name="stripe_output.svg", mime="image/svg+xml")
    st.code(svg_code, language="xml")