#!/usr/bin/env python3
import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import markdown
import requests


TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
UPLOAD_IMG_URL = "https://api.weixin.qq.com/cgi-bin/media/uploadimg"
DRAFT_ADD_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"
ADD_MATERIAL_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material"


THEME_STYLES = {
    "clean": {
        "h1": "font-size:28px;line-height:1.4;margin:0 0 20px;color:#111;font-weight:700;",
        "h2": "font-size:22px;line-height:1.45;margin:28px 0 12px;color:#0f172a;font-weight:700;padding-left:10px;border-left:4px solid #07c160;",
        "h3": "font-size:18px;line-height:1.45;margin:20px 0 10px;color:#1f2937;font-weight:700;",
        "p": "font-size:16px;line-height:1.85;margin:12px 0;color:#1f2329;",
        "blockquote": "margin:16px 0;padding:10px 12px;border-left:4px solid #95a5a6;background:#f8fafc;color:#4b5563;",
        "ul": "margin:10px 0 10px 22px;padding:0;",
        "ol": "margin:10px 0 10px 22px;padding:0;",
        "li": "margin:6px 0;line-height:1.75;color:#1f2329;",
        "img": "display:block;max-width:100%;height:auto;margin:16px auto;border-radius:6px;",
        "hr": "margin:22px 0;border:none;border-top:1px solid #e5e7eb;",
        "code": "font-family:Menlo,Consolas,monospace;background:#f3f4f6;padding:2px 4px;border-radius:4px;font-size:0.92em;",
        "pre": "background:#111827;color:#f3f4f6;padding:12px;border-radius:8px;overflow:auto;",
        "table": "border-collapse:collapse;width:100%;margin:14px 0;",
        "th": "border:1px solid #e5e7eb;background:#f8fafc;padding:8px;text-align:left;",
        "td": "border:1px solid #e5e7eb;padding:8px;",
        "a": "color:#0ea5e9;text-decoration:none;",
    },
    "card": {
        "h1": "font-size:30px;line-height:1.35;margin:0 0 22px;color:#0f172a;font-weight:800;",
        "h2": "font-size:22px;line-height:1.4;margin:28px 0 12px;color:#0f172a;font-weight:700;background:#f8fafc;padding:10px 12px;border-radius:8px;",
        "h3": "font-size:18px;line-height:1.45;margin:20px 0 10px;color:#1f2937;font-weight:700;",
        "p": "font-size:16px;line-height:1.9;margin:12px 0;color:#1f2329;",
        "blockquote": "margin:16px 0;padding:12px;border-radius:8px;background:#f8fafc;color:#4b5563;",
        "ul": "margin:10px 0 10px 22px;padding:0;",
        "ol": "margin:10px 0 10px 22px;padding:0;",
        "li": "margin:6px 0;line-height:1.75;color:#1f2329;",
        "img": "display:block;max-width:100%;height:auto;margin:18px auto;border-radius:10px;",
        "hr": "margin:24px 0;border:none;border-top:1px dashed #cbd5e1;",
        "code": "font-family:Menlo,Consolas,monospace;background:#f1f5f9;padding:2px 4px;border-radius:4px;font-size:0.92em;",
        "pre": "background:#0f172a;color:#f8fafc;padding:12px;border-radius:10px;overflow:auto;",
        "table": "border-collapse:collapse;width:100%;margin:14px 0;border-radius:8px;overflow:hidden;",
        "th": "border:1px solid #e2e8f0;background:#f8fafc;padding:8px;text-align:left;",
        "td": "border:1px solid #e2e8f0;padding:8px;",
        "a": "color:#2563eb;text-decoration:none;",
    },
    "tech": {
        "h1": "font-size:28px;line-height:1.4;margin:0 0 20px;color:#0b1220;font-weight:800;",
        "h2": "font-size:22px;line-height:1.45;margin:28px 0 12px;color:#0b1220;font-weight:700;border-bottom:2px solid #0ea5e9;padding-bottom:6px;",
        "h3": "font-size:18px;line-height:1.45;margin:20px 0 10px;color:#1e293b;font-weight:700;",
        "p": "font-size:16px;line-height:1.85;margin:12px 0;color:#111827;",
        "blockquote": "margin:16px 0;padding:12px;border-left:4px solid #0ea5e9;background:#f0f9ff;color:#334155;",
        "ul": "margin:10px 0 10px 22px;padding:0;",
        "ol": "margin:10px 0 10px 22px;padding:0;",
        "li": "margin:6px 0;line-height:1.75;color:#111827;",
        "img": "display:block;max-width:100%;height:auto;margin:16px auto;border:1px solid #e5e7eb;",
        "hr": "margin:22px 0;border:none;border-top:1px solid #cbd5e1;",
        "code": "font-family:Menlo,Consolas,monospace;background:#e2e8f0;padding:2px 4px;border-radius:4px;font-size:0.92em;",
        "pre": "background:#0f172a;color:#e2e8f0;padding:12px;border-radius:6px;overflow:auto;",
        "table": "border-collapse:collapse;width:100%;margin:14px 0;",
        "th": "border:1px solid #cbd5e1;background:#e2e8f0;padding:8px;text-align:left;",
        "td": "border:1px solid #cbd5e1;padding:8px;",
        "a": "color:#0284c7;text-decoration:none;",
    },
    "minimal": {
        "h1": "font-size:27px;line-height:1.45;margin:0 0 18px;color:#1a1a1a;font-weight:700;",
        "h2": "font-size:21px;line-height:1.5;margin:30px 0 12px;color:#222;font-weight:700;",
        "h3": "font-size:17px;line-height:1.5;margin:20px 0 10px;color:#2b2b2b;font-weight:700;",
        "p": "font-size:16px;line-height:1.9;margin:12px 0;color:#2a2a2a;",
        "blockquote": "margin:16px 0;padding:10px 12px;border-left:3px solid #d1d5db;background:#fafafa;color:#4b5563;",
        "ul": "margin:10px 0 10px 22px;padding:0;",
        "ol": "margin:10px 0 10px 22px;padding:0;",
        "li": "margin:6px 0;line-height:1.8;color:#2a2a2a;",
        "img": "display:block;max-width:100%;height:auto;margin:16px auto;",
        "hr": "margin:24px 0;border:none;border-top:1px solid #e5e7eb;",
        "code": "font-family:Menlo,Consolas,monospace;background:#f4f4f5;padding:2px 4px;border-radius:4px;font-size:0.92em;",
        "pre": "background:#f8fafc;color:#1f2937;padding:12px;border-radius:8px;overflow:auto;border:1px solid #e5e7eb;",
        "table": "border-collapse:collapse;width:100%;margin:14px 0;",
        "th": "border:1px solid #e5e7eb;background:#fafafa;padding:8px;text-align:left;",
        "td": "border:1px solid #e5e7eb;padding:8px;",
        "a": "color:#2563eb;text-decoration:none;",
    },
    "wechat-classic": {
        "h1": "font-size:28px;line-height:1.45;margin:0 0 20px;color:#111827;font-weight:700;text-align:center;",
        "h2": "font-size:21px;line-height:1.45;margin:30px 0 14px;color:#111827;font-weight:700;background:#f6f7fb;border-left:4px solid #07c160;padding:8px 10px;",
        "h3": "font-size:17px;line-height:1.45;margin:22px 0 10px;color:#1f2937;font-weight:700;",
        "p": "font-size:16px;line-height:1.9;margin:12px 0;color:#1f2329;",
        "blockquote": "margin:16px 0;padding:12px;border-radius:8px;background:#f6f7fb;color:#4b5563;",
        "ul": "margin:10px 0 10px 22px;padding:0;",
        "ol": "margin:10px 0 10px 22px;padding:0;",
        "li": "margin:6px 0;line-height:1.8;color:#1f2329;",
        "img": "display:block;max-width:100%;height:auto;margin:18px auto;border-radius:8px;",
        "hr": "margin:24px 0;border:none;border-top:1px dashed #cbd5e1;",
        "code": "font-family:Menlo,Consolas,monospace;background:#eef2ff;padding:2px 4px;border-radius:4px;font-size:0.92em;",
        "pre": "background:#0f172a;color:#f8fafc;padding:12px;border-radius:8px;overflow:auto;",
        "table": "border-collapse:collapse;width:100%;margin:14px 0;",
        "th": "border:1px solid #dbe3ef;background:#f6f7fb;padding:8px;text-align:left;",
        "td": "border:1px solid #dbe3ef;padding:8px;",
        "a": "color:#0ea5e9;text-decoration:none;",
    },
    "ai-insight": {
        "h1": "font-size:30px;line-height:1.4;margin:0 0 22px;color:#0f172a;font-weight:800;letter-spacing:0.2px;",
        "h2": "font-size:22px;line-height:1.45;margin:30px 0 14px;color:#0f172a;font-weight:700;border-left:5px solid #6366f1;background:#f8faff;padding:8px 12px;border-radius:8px;",
        "h3": "font-size:18px;line-height:1.45;margin:22px 0 10px;color:#1e293b;font-weight:700;",
        "p": "font-size:16px;line-height:1.95;margin:12px 0;color:#111827;",
        "blockquote": "margin:16px 0;padding:12px 14px;border-left:4px solid #22c55e;background:#f6fffb;color:#374151;border-radius:6px;",
        "ul": "margin:10px 0 10px 22px;padding:0;",
        "ol": "margin:10px 0 10px 22px;padding:0;",
        "li": "margin:7px 0;line-height:1.85;color:#111827;",
        "img": "display:block;max-width:100%;height:auto;margin:18px auto;border-radius:10px;border:1px solid #e5e7eb;",
        "hr": "margin:24px 0;border:none;border-top:1px solid #dbe3ef;",
        "code": "font-family:Menlo,Consolas,monospace;background:#eef2ff;padding:2px 5px;border-radius:4px;font-size:0.92em;color:#4338ca;",
        "pre": "background:#0b1220;color:#e2e8f0;padding:13px;border-radius:10px;overflow:auto;",
        "table": "border-collapse:collapse;width:100%;margin:16px 0;",
        "th": "border:1px solid #dbe3ef;background:#eef2ff;padding:8px;text-align:left;color:#1e293b;",
        "td": "border:1px solid #dbe3ef;padding:8px;",
        "a": "color:#4f46e5;text-decoration:none;",
    },
}


def _strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and ((value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")):
        return value[1:-1]
    return value


def load_env_local(start_dir: Path, filename: str = ".env.local") -> Optional[Path]:
    """Load KEY=VALUE pairs from nearest .env.local (walking parents) into os.environ.

    Only sets keys that are not already present in the environment.
    """
    current = start_dir
    for parent in [current, *current.parents]:
        candidate = parent / filename
        if not candidate.exists():
            continue
        try:
            for line in candidate.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                if "=" not in stripped:
                    continue
                key, raw_value = stripped.split("=", 1)
                key = key.strip()
                if not key:
                    continue
                if key in os.environ:
                    continue
                os.environ[key] = _strip_quotes(raw_value)
        except Exception:
            return None
        return candidate
    return None


def find_workspace_root(start_dir: Path) -> Path:
    for parent in [start_dir, *start_dir.parents]:
        if (parent / ".git").exists() or (parent / "AGENTS.md").exists():
            return parent
    return start_dir


@dataclass
class WeChatConfig:
    app_id: str
    app_secret: str
    token_cache_file: Path


class WeChatClient:
    def __init__(self, config: WeChatConfig):
        self.config = config

    def _read_token_cache(self) -> Optional[dict]:
        if not self.config.token_cache_file.exists():
            return None
        try:
            return json.loads(self.config.token_cache_file.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _write_token_cache(self, payload: dict) -> None:
        self.config.token_cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.config.token_cache_file.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def get_access_token(self, force_refresh: bool = False) -> str:
        cached = self._read_token_cache()
        now = int(time.time())
        if not force_refresh and cached:
            token = cached.get("access_token")
            expires_at = int(cached.get("expires_at", 0))
            if token and expires_at - 120 > now:
                return token

        response = requests.get(
            TOKEN_URL,
            params={
                "grant_type": "client_credential",
                "appid": self.config.app_id,
                "secret": self.config.app_secret,
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("errcode"):
            errcode = payload.get("errcode")
            errmsg = payload.get("errmsg")
            if errcode == 40164:
                raise RuntimeError(
                    "get_access_token failed: invalid ip (errcode 40164). "
                    "Your WeChat Official Account backend has IP whitelist enabled; "
                    "add your current public egress IP to the whitelist or disable the whitelist. "
                    f"details: {errmsg}"
                )
            raise RuntimeError(f"get_access_token failed: {payload}")

        token = payload.get("access_token")
        expires_in = int(payload.get("expires_in", 7200))
        if not token:
            raise RuntimeError(f"invalid token response: {payload}")

        cache_payload = {
            "access_token": token,
            "expires_at": now + expires_in,
        }
        self._write_token_cache(cache_payload)
        return token

    def upload_image(self, image_path: Path) -> str:
        token = self.get_access_token()
        with image_path.open("rb") as file_handle:
            response = requests.post(
                UPLOAD_IMG_URL,
                params={"access_token": token},
                files={"media": file_handle},
                timeout=60,
            )
        response.raise_for_status()
        payload = response.json()
        if payload.get("errcode"):
            if payload.get("errcode") in {40014, 42001, 42007}:
                token = self.get_access_token(force_refresh=True)
                with image_path.open("rb") as file_handle:
                    retry_response = requests.post(
                        UPLOAD_IMG_URL,
                        params={"access_token": token},
                        files={"media": file_handle},
                        timeout=60,
                    )
                retry_response.raise_for_status()
                payload = retry_response.json()
            if payload.get("errcode"):
                raise RuntimeError(f"upload_image failed for {image_path}: {payload}")

        image_url = payload.get("url")
        if not image_url:
            raise RuntimeError(f"upload_image missing url for {image_path}: {payload}")
        return image_url

    def create_draft(
        self,
        title: str,
        content_html: str,
        thumb_media_id: str,
        author: str = "paper2wechat",
        digest: str = "",
        content_source_url: str = "",
    ) -> dict:
        token = self.get_access_token()
        body = {
            "articles": [
                {
                    "title": title,
                    "author": author,
                    "digest": digest,
                    "content": content_html,
                    "content_source_url": content_source_url,
                    "thumb_media_id": thumb_media_id,
                }
            ]
        }
        response = requests.post(
            DRAFT_ADD_URL,
            params={"access_token": token},
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("errcode"):
            raise RuntimeError(f"create_draft failed: {payload}")
        return payload

    def upload_permanent_image(self, image_path: Path) -> str:
        token = self.get_access_token()
        with image_path.open("rb") as file_handle:
            response = requests.post(
                ADD_MATERIAL_URL,
                params={"access_token": token, "type": "image"},
                files={"media": file_handle},
                timeout=60,
            )
        response.raise_for_status()
        payload = response.json()
        if payload.get("errcode"):
            if payload.get("errcode") in {40014, 42001, 42007}:
                token = self.get_access_token(force_refresh=True)
                with image_path.open("rb") as file_handle:
                    retry_response = requests.post(
                        ADD_MATERIAL_URL,
                        params={"access_token": token, "type": "image"},
                        files={"media": file_handle},
                        timeout=60,
                    )
                retry_response.raise_for_status()
                payload = retry_response.json()
            if payload.get("errcode"):
                raise RuntimeError(
                    f"upload_permanent_image failed for {image_path}: {payload}"
                )
        media_id = payload.get("media_id")
        if not media_id:
            raise RuntimeError(
                f"upload_permanent_image missing media_id for {image_path}: {payload}"
            )
        return media_id


def find_markdown_images(md_text: str) -> List[Tuple[str, str]]:
    pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
    return [
        (match.group(1), match.group(2).strip()) for match in pattern.finditer(md_text)
    ]


def replace_markdown_image_paths(md_text: str, replace_map: Dict[str, str]) -> str:
    pattern = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")

    def _replace(match: re.Match) -> str:
        alt_text = match.group(1)
        original_path = match.group(2).strip()
        new_path = replace_map.get(original_path)
        if not new_path:
            return match.group(0)
        return f"![{alt_text}]({new_path})"

    return pattern.sub(_replace, md_text)


def markdown_to_html(md_text: str) -> str:
    return markdown.markdown(md_text, extensions=["extra", "tables", "fenced_code"])


def normalize_markdown_for_wechat(md_text: str) -> str:
    normalized = re.sub(r"\*\*([^*\n]+)\*\*\s*:", r"**\1：**", md_text)

    lines = normalized.splitlines()
    fixed_lines: List[str] = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("> - "):
            previous = fixed_lines[-1].strip() if fixed_lines else ""
            if previous.startswith(">") and not previous.startswith("> -") and previous != ">":
                fixed_lines.append(">")
        fixed_lines.append(line)
    return "\n".join(fixed_lines)


def stabilize_label_colon_spacing(article_html: str) -> str:
    """Reduce accidental line breaks after label colons in pasted WeChat editor.

    Example: <strong>问题：</strong> 文本 -> <strong>问题：</strong>&nbsp;文本
    """
    pattern = re.compile(r"(<strong[^>]*>[^<]{1,40}[：:]\s*</strong>)\s+")
    return pattern.sub(r"\1&nbsp;", article_html)


def stabilize_label_inline_layout(article_html: str) -> str:
    """Convert strong label patterns to span-based inline layout for WeChat paste stability.

    Some WeChat editor paste paths split <strong>label:</strong> and content into separate lines.
    This rewrite uses span + nowrap label to reduce forced line breaks.
    """

    def _rewrite_list_item(match: re.Match) -> str:
        prefix = match.group(1)
        label = match.group(2).strip()
        suffix = match.group(3).strip()
        return (
            f'{prefix}<span style="font-weight:700;white-space:nowrap;">{label}</span>'
            f'<span style="display:inline;">&nbsp;{suffix}</span></li>'
        )

    li_pattern = re.compile(
        r"(<li[^>]*>)\s*<strong[^>]*>([^<]{1,40}[：:])\s*</strong>\s*(.*?)\s*</li>",
        flags=re.IGNORECASE | re.DOTALL,
    )
    article_html = li_pattern.sub(_rewrite_list_item, article_html)

    def _rewrite_paragraph(match: re.Match) -> str:
        prefix = match.group(1)
        label = match.group(2).strip()
        suffix = match.group(3).strip()
        return (
            f'{prefix}<span style="font-weight:700;white-space:nowrap;">{label}</span>'
            f'<span style="display:inline;">&nbsp;{suffix}</span></p>'
        )

    p_pattern = re.compile(
        r"(<p[^>]*>)\s*<strong[^>]*>([^<]{1,40}[：:])\s*</strong>\s*(.*?)\s*</p>",
        flags=re.IGNORECASE | re.DOTALL,
    )
    return p_pattern.sub(_rewrite_paragraph, article_html)


def _apply_style_to_tag(html_text: str, tag: str, style_text: str) -> str:
    pattern = re.compile(rf"<{tag}(\\s[^>]*)?>", re.IGNORECASE)

    def _replace(match: re.Match) -> str:
        attrs = match.group(1) or ""
        style_match = re.search(r'style\\s*=\\s*"([^"]*)"', attrs, flags=re.IGNORECASE)
        if style_match:
            existing_style = style_match.group(1).strip()
            combined_style = f"{existing_style};{style_text}" if existing_style else style_text
            new_attrs = re.sub(
                r'style\\s*=\\s*"[^"]*"',
                f'style="{combined_style}"',
                attrs,
                flags=re.IGNORECASE,
            )
        else:
            new_attrs = f'{attrs} style="{style_text}"'
        return f"<{tag}{new_attrs}>"

    return pattern.sub(_replace, html_text)


def apply_theme_styles(article_html: str, theme: str) -> str:
    style_pack = THEME_STYLES.get(theme, THEME_STYLES["clean"])
    themed_html = article_html
    for tag, style_text in style_pack.items():
        themed_html = _apply_style_to_tag(themed_html, tag, style_text)
    return themed_html


def build_paste_html(article_html: str, title: str) -> str:
    escaped_title = html.escape(title)
    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escaped_title} - WeChat Paste</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, \"PingFang SC\", \"Helvetica Neue\", sans-serif; margin: 24px auto; max-width: 860px; padding: 0 16px; color: #1f2329; }}
    .toolbar {{ position: sticky; top: 0; background: #fff; padding: 12px 0; border-bottom: 1px solid #e5e6eb; margin-bottom: 20px; }}
    button {{ background: #07c160; color: #fff; border: none; border-radius: 8px; padding: 10px 16px; font-size: 14px; cursor: pointer; }}
    button:disabled {{ opacity: 0.6; cursor: not-allowed; }}
    #status {{ margin-left: 12px; font-size: 13px; color: #4e5969; }}
    #article-content img {{ max-width: 100%; height: auto; }}
  </style>
</head>
<body>
  <div class=\"toolbar\">
    <button id=\"copy-btn\">复制到公众号（富文本）</button>
    <span id=\"status\">点击按钮后去公众号编辑器粘贴</span>
  </div>
  <div id=\"article-content\">{article_html}</div>
  <script>
    const copyBtn = document.getElementById('copy-btn');
    const status = document.getElementById('status');
    copyBtn.addEventListener('click', async () => {{
      const content = document.getElementById('article-content');
      const htmlData = content.innerHTML;
      const textData = content.innerText;
      try {{
        if (navigator.clipboard && window.ClipboardItem) {{
          const item = new ClipboardItem({{
            'text/html': new Blob([htmlData], {{ type: 'text/html' }}),
            'text/plain': new Blob([textData], {{ type: 'text/plain' }}),
          }});
          await navigator.clipboard.write([item]);
          status.textContent = '已复制富文本，可直接粘贴到公众号编辑器';
          return;
        }}
      }} catch (e) {{}}
      const range = document.createRange();
      range.selectNodeContents(content);
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      const ok = document.execCommand('copy');
      selection.removeAllRanges();
      status.textContent = ok ? '已复制（兼容模式），请粘贴到公众号编辑器' : '复制失败，请手动全选复制';
    }});
  </script>
</body>
</html>
"""


def build_theme_preview_html(title: str, themed_articles: Dict[str, str]) -> str:
    escaped_title = html.escape(title)
    theme_keys = sorted(themed_articles.keys())
    themes_json = json.dumps(themed_articles, ensure_ascii=False)
    options_html = "".join(
        f'<option value="{html.escape(theme)}">{html.escape(theme)}</option>'
        for theme in theme_keys
    )
    return f"""<!doctype html>
<html lang=\"zh-CN\">
<head>
    <meta charset=\"UTF-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{escaped_title} - Theme Preview</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, \"PingFang SC\", \"Helvetica Neue\", sans-serif; margin: 24px auto; max-width: 960px; padding: 0 16px; color: #1f2329; }}
        .toolbar {{ position: sticky; top: 0; background: #fff; padding: 12px 0; border-bottom: 1px solid #e5e6eb; margin-bottom: 20px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
        select, button {{ border: 1px solid #d0d7de; border-radius: 8px; padding: 8px 12px; font-size: 14px; background: #fff; }}
        button {{ background: #07c160; color: #fff; border-color: #07c160; cursor: pointer; }}
        #status {{ font-size: 13px; color: #4e5969; }}
    </style>
</head>
<body>
    <div class=\"toolbar\">
        <label for=\"theme\">主题</label>
        <select id=\"theme\">{options_html}</select>
        <button id=\"copy-btn\">复制当前主题到公众号</button>
        <span id=\"status\">可切换主题并实时预览</span>
    </div>
    <div id=\"article-content\"></div>
    <script>
        const themedArticles = {themes_json};
        const themeSelect = document.getElementById('theme');
        const article = document.getElementById('article-content');
        const status = document.getElementById('status');
        function renderTheme() {{
            const theme = themeSelect.value;
            article.innerHTML = themedArticles[theme] || '';
            status.textContent = `已切换主题：${{theme}}`;
        }}
        renderTheme();
        themeSelect.addEventListener('change', renderTheme);
        document.getElementById('copy-btn').addEventListener('click', async () => {{
            const htmlData = article.innerHTML;
            const textData = article.innerText;
            try {{
                if (navigator.clipboard && window.ClipboardItem) {{
                    const item = new ClipboardItem({{
                        'text/html': new Blob([htmlData], {{ type: 'text/html' }}),
                        'text/plain': new Blob([textData], {{ type: 'text/plain' }}),
                    }});
                    await navigator.clipboard.write([item]);
                    status.textContent = '已复制当前主题富文本，可直接粘贴到公众号编辑器';
                    return;
                }}
            }} catch (e) {{}}
            const range = document.createRange();
            range.selectNodeContents(article);
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(range);
            const ok = document.execCommand('copy');
            selection.removeAllRanges();
            status.textContent = ok ? '已复制（兼容模式）' : '复制失败，请手动全选复制';
        }});
    </script>
</body>
</html>
"""


def infer_title(md_text: str, fallback: str) -> str:
    for line in md_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def truncate_chars(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text.strip()
    return text[:max_chars].strip()


def build_title_candidates(title: str) -> List[str]:
    candidates: List[str] = []

    def _add(value: str) -> None:
        value = value.strip()
        if value and value not in candidates:
            candidates.append(value)

    _add(title)
    for limit in [64, 56, 48, 40, 32, 28, 24, 20, 16]:
        _add(truncate_chars(title, max_chars=limit))
    return candidates


def strip_first_h1_from_html(article_html: str) -> str:
    pattern = re.compile(r"\s*<h1\b[^>]*>.*?</h1>\s*", flags=re.IGNORECASE | re.DOTALL)
    return pattern.sub("", article_html, count=1)


def is_remote_path(path_text: str) -> bool:
    lowered = path_text.lower()
    return (
        lowered.startswith("http://")
        or lowered.startswith("https://")
        or lowered.startswith("data:")
    )


def resolve_output_paths(
    input_md: Path, out_html: Optional[str], out_paste_html: Optional[str]
) -> Tuple[Path, Path]:
    stem = input_md.stem
    parent = input_md.parent
    html_path = Path(out_html) if out_html else parent / f"{stem}.wechat.html"
    paste_path = (
        Path(out_paste_html) if out_paste_html else parent / f"{stem}.wechat.paste.html"
    )
    return html_path, paste_path


def load_existing_image_map(image_map_path: Path) -> Dict[str, str]:
    if not image_map_path.exists():
        return {}
    try:
        payload = json.loads(image_map_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    mapping = payload.get("images")
    if isinstance(mapping, dict):
        output: Dict[str, str] = {}
        for key, value in mapping.items():
            if isinstance(value, str):
                output[str(key)] = value
                continue
            if isinstance(value, dict):
                url = value.get("url")
                if isinstance(url, str) and url:
                    output[str(key)] = url
        return output
    return {}


def persist_image_map(image_map_path: Path, mapping: Dict[str, str]) -> None:
    image_map_path.write_text(
        json.dumps({"images": mapping}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def file_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with file_path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_existing_image_hash_map(image_hash_map_path: Path) -> Dict[str, str]:
    if not image_hash_map_path.exists():
        return {}
    try:
        payload = json.loads(image_hash_map_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    mapping = payload.get("images")
    if isinstance(mapping, dict):
        return {str(key): str(value) for key, value in mapping.items()}
    return {}


def persist_image_hash_map(image_hash_map_path: Path, mapping: Dict[str, str]) -> None:
    image_hash_map_path.write_text(
        json.dumps({"images": mapping}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def pick_cover_image_ref(markdown_images: List[Tuple[str, str]]) -> Optional[str]:
    if not markdown_images:
        return None

    preferred = ["框架", "总览", "overview", "pipeline", "方法", "架构", "workflow"]
    secondary = ["执行", "场景", "可视化", "demo", "案例"]
    less_preferred = ["结果", "对比", "ablation", "消融", "表格", "dataset"]

    scored: List[Tuple[int, int, str]] = []
    for index, (alt_text, image_ref) in enumerate(markdown_images):
        lowered = (alt_text or "").lower()
        score = 50
        for keyword in preferred:
            if keyword in lowered:
                score += 60
        for keyword in secondary:
            if keyword in lowered:
                score += 25
        for keyword in less_preferred:
            if keyword in lowered:
                score -= 15
        scored.append((score, -index, image_ref))

    scored.sort(reverse=True)
    return scored[0][2]


def publish(args: argparse.Namespace) -> None:
    input_md = Path(args.input_md).expanduser().resolve()
    if not input_md.exists():
        raise FileNotFoundError(f"input markdown not found: {input_md}")

    if args.upload_images or args.create_draft:
        load_env_local(start_dir=input_md.parent)

    workspace_root = find_workspace_root(input_md.parent)

    md_text = input_md.read_text(encoding="utf-8")
    normalized_md_text = normalize_markdown_for_wechat(md_text)
    output_html_path, output_paste_path = resolve_output_paths(
        input_md, args.out_html, args.out_paste_html
    )

    image_map_path = (
        Path(args.image_map).expanduser().resolve()
        if args.image_map
        else input_md.parent / "image-map.json"
    )
    image_hash_map_path = (
        Path(args.image_hash_map).expanduser().resolve()
        if args.image_hash_map
        else input_md.parent / "image-hash-map.json"
    )
    image_map = load_existing_image_map(image_map_path)
    image_hash_map = load_existing_image_hash_map(image_hash_map_path)
    replace_map: Dict[str, str] = {}
    markdown_images = find_markdown_images(normalized_md_text)

    client = None
    if args.upload_images or args.create_draft:
        app_id = args.app_id or args.wechat_app_id or os.environ.get("WECHAT_APP_ID")
        app_secret = (
            args.app_secret
            or args.wechat_app_secret
            or os.environ.get("WECHAT_APP_SECRET")
        )
        if not app_id or not app_secret:
            raise ValueError(
                "app_id/app_secret required for upload_images or create_draft. "
                "Provide --app-id/--app-secret or set WECHAT_APP_ID/WECHAT_APP_SECRET."
            )
        token_cache_file = (
            Path(args.token_cache).expanduser().resolve()
            if args.token_cache
            else workspace_root / ".wechat-token.json"
        )
        client = WeChatClient(
            WeChatConfig(
                app_id=app_id,
                app_secret=app_secret,
                token_cache_file=token_cache_file,
            )
        )

    if args.upload_images:
        if client is None:
            raise RuntimeError("WeChat client is not initialized")
        for _, image_ref in markdown_images:
            if is_remote_path(image_ref):
                continue
            absolute_image = (input_md.parent / image_ref).resolve()
            if not absolute_image.exists():
                print(
                    f"[warn] image not found, skip upload: {image_ref}", file=sys.stderr
                )
                continue
            cache_key = str(absolute_image)
            current_hash = file_sha256(absolute_image)
            uploaded_url = image_map.get(cache_key)
            cached_hash = image_hash_map.get(cache_key)
            if not uploaded_url or cached_hash != current_hash:
                uploaded_url = client.upload_image(absolute_image)
                image_map[cache_key] = uploaded_url
                image_hash_map[cache_key] = current_hash
                print(f"[uploaded] {image_ref} -> {uploaded_url}", file=sys.stderr)
            replace_map[image_ref] = uploaded_url
        persist_image_map(image_map_path, image_map)
        persist_image_hash_map(image_hash_map_path, image_hash_map)

    rewritten_md = replace_markdown_image_paths(normalized_md_text, replace_map)
    base_article_html = markdown_to_html(rewritten_md)
    base_article_html = stabilize_label_colon_spacing(base_article_html)
    base_article_html = stabilize_label_inline_layout(base_article_html)
    article_html = apply_theme_styles(base_article_html, theme=args.theme)
    themed_articles = {
        theme_name: apply_theme_styles(base_article_html, theme=theme_name)
        for theme_name in sorted(THEME_STYLES.keys())
    }

    output_html_path.parent.mkdir(parents=True, exist_ok=True)
    output_paste_path.parent.mkdir(parents=True, exist_ok=True)

    output_html_path.write_text(article_html, encoding="utf-8")
    title = args.title or infer_title(md_text, fallback=input_md.stem)
    paste_html = build_paste_html(article_html, title=title)
    output_paste_path.write_text(paste_html, encoding="utf-8")

    preview_file = (
        Path(args.theme_preview_file).expanduser().resolve()
        if args.theme_preview_file
        else input_md.parent / f"{input_md.stem}.wechat.themes.html"
    )
    preview_html = build_theme_preview_html(
        title=title, themed_articles=themed_articles
    )
    preview_file.write_text(preview_html, encoding="utf-8")

    print(f"[ok] article html: {output_html_path}")
    print(f"[ok] paste html: {output_paste_path}")
    print(f"[ok] theme preview: {preview_file}")
    if args.upload_images:
        print(f"[ok] image map: {image_map_path}")
        print(f"[ok] image hash map: {image_hash_map_path}")

    if args.create_draft:
        if client is None:
            raise RuntimeError("WeChat client is not initialized")
        title_candidates = build_title_candidates(title)
        draft_title = title_candidates[0] if title_candidates else input_md.stem
        draft_content_html = (
            article_html if args.keep_h1_in_draft else strip_first_h1_from_html(article_html)
        )
        thumb_media_id = args.thumb_media_id
        if not thumb_media_id and args.auto_thumb:
            cover_ref = pick_cover_image_ref(markdown_images)
            if cover_ref and not is_remote_path(cover_ref):
                cover_abs = (input_md.parent / cover_ref).resolve()
                if cover_abs.exists():
                    thumb_media_id = client.upload_permanent_image(cover_abs)
                    print(
                        f"[ok] auto thumb selected: {cover_ref} -> {thumb_media_id}",
                        file=sys.stderr,
                    )
        if not thumb_media_id:
            raise ValueError(
                "--thumb-media-id is required when --create-draft is enabled. "
                "Or use --auto-thumb to pick one image from markdown automatically."
            )
        draft_payload = None
        last_error: Optional[Exception] = None
        for candidate_title in title_candidates or [draft_title]:
            try:
                draft_payload = client.create_draft(
                    title=candidate_title,
                    content_html=draft_content_html,
                    thumb_media_id=thumb_media_id,
                    author=args.author,
                    digest=args.digest,
                    content_source_url=args.content_source_url,
                )
                draft_title = candidate_title
                break
            except RuntimeError as error:
                last_error = error
                if "45003" in str(error):
                    print(
                        f"[warn] draft title limit hit, retrying with shorter title: {candidate_title}",
                        file=sys.stderr,
                    )
                    continue
                raise
        if draft_payload is None:
            if last_error:
                raise last_error
            raise RuntimeError("create_draft failed with unknown error")
        result_file = (
            Path(args.publish_result).expanduser().resolve()
            if args.publish_result
            else input_md.parent / "publish-result.json"
        )
        result_file.write_text(
            json.dumps(draft_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[ok] draft result: {result_file}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Publish local markdown article to WeChat-friendly outputs"
    )
    parser.add_argument(
        "--input-md", required=True, help="Path to article markdown file"
    )

    parser.add_argument(
        "--upload-images",
        action="store_true",
        help="Upload local markdown images to WeChat",
    )
    parser.add_argument(
        "--create-draft",
        action="store_true",
        help="Create a WeChat draft using rendered html",
    )
    parser.add_argument(
        "--theme",
        choices=sorted(THEME_STYLES.keys()),
        default="clean",
        help="Render style theme for generated html and draft content",
    )
    parser.add_argument(
        "--auto-thumb",
        action="store_true",
        help="Automatically choose one markdown image as draft cover and upload it as permanent image",
    )
    parser.add_argument(
        "--keep-h1-in-draft",
        action="store_true",
        help="Keep first H1 heading in draft content body (default removes it to avoid title duplication)",
    )

    parser.add_argument("--out-html", default=None, help="Output HTML file path")
    parser.add_argument(
        "--out-paste-html", default=None, help="Output paste-helper HTML file path"
    )
    parser.add_argument("--image-map", default=None, help="Image map json path")
    parser.add_argument(
        "--image-hash-map",
        default=None,
        help="Image hash map json path for upload dedupe",
    )
    parser.add_argument(
        "--publish-result", default=None, help="Draft publish result json path"
    )
    parser.add_argument(
        "--theme-preview-file",
        default=None,
        help="Theme switch preview html path",
    )

    parser.add_argument("--app-id", default=None, help="WeChat app id")
    parser.add_argument("--app-secret", default=None, help="WeChat app secret")
    parser.add_argument(
        "--wechat-app-id", dest="wechat_app_id", default=None, help="Alias for app id"
    )
    parser.add_argument(
        "--wechat-app-secret",
        dest="wechat_app_secret",
        default=None,
        help="Alias for app secret",
    )
    parser.add_argument("--token-cache", default=None, help="Token cache file path")

    parser.add_argument(
        "--title",
        default=None,
        help="Draft title, inferred from markdown heading if omitted",
    )
    parser.add_argument("--author", default="paper2wechat", help="Draft author")
    parser.add_argument("--digest", default="", help="Draft digest")
    parser.add_argument("--content-source-url", default="", help="Draft source URL")
    parser.add_argument(
        "--thumb-media-id", default=None, help="Draft cover image media id"
    )

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        publish(args)
        return 0
    except Exception as error:
        print(f"[error] {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
