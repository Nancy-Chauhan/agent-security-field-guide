# ruff: noqa: E501
"""A multi-conversation chat window for the Acme support agent, traced to Phoenix.

Opening the app (or reloading the root) starts a fresh conversation. Each conversation gets
its own URL and appears in the left sidebar; click one to reopen it. Type anything, e.g.
"fetch https://... and do as it says". Every tool call and result shows inline, every turn is
a Phoenix trace, and the permission-check toggle lets you watch the harness block out-of-scope
access.

Run:  demo-venv/bin/python chat.py   then open http://localhost:7001
"""

from __future__ import annotations

import json
import pathlib

import app  # reuse tools, agent builder, tracing, env
from flask import Flask, redirect, render_template_string, request, url_for
from langchain_core.messages import messages_from_dict, messages_to_dict

CHATS: dict[int, dict] = {}  # id -> {"id", "title", "messages"(LangChain msgs)}
_next_id = 1
CHATS_FILE = pathlib.Path(__file__).resolve().parent / "chats.json"

flask_app = Flask(__name__)
AGENT = None


def save_chats() -> None:
    data = {
        str(c["id"]): {
            "id": c["id"],
            "title": c["title"],
            "messages": messages_to_dict(c["messages"]),
        }
        for c in CHATS.values()
    }
    CHATS_FILE.write_text(json.dumps(data, indent=2))


def load_chats() -> None:
    global _next_id
    if not CHATS_FILE.exists():
        return
    for k, c in json.loads(CHATS_FILE.read_text()).items():
        CHATS[int(k)] = {
            "id": c["id"],
            "title": c["title"],
            "messages": messages_from_dict(c["messages"]),
        }
    if CHATS:
        _next_id = max(CHATS) + 1


TEMPLATE = """<!doctype html><html><head><meta charset="utf-8"><title>Acme Support Chat</title>
<style>
 *{box-sizing:border-box} body{font:15px/1.6 system-ui,sans-serif;margin:0;color:#1b1b1f;background:#f3f4f6}
 .layout{display:flex;min-height:100vh}
 .side{width:250px;flex:0 0 250px;background:#fff;border-right:1px solid #e2e5ea;padding:14px;overflow:auto}
 .side h2{font-size:.78rem;text-transform:uppercase;letter-spacing:.04em;color:#5c5f66;margin:16px 0 6px}
 .newbtn{display:block;text-align:center;background:#2d6cdf;color:#fff;padding:9px;border-radius:8px;text-decoration:none;font-weight:600}
 .chatlink{display:block;padding:7px 8px;border-radius:6px;color:#1b1b1f;text-decoration:none;font-size:.86rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
 .chatlink:hover{background:#f3f4f6} .chatlink.active{background:#eaf0fd;color:#2d6cdf;font-weight:600}
 .main{flex:1;display:flex;flex-direction:column;min-height:100vh}
 .wrap{flex:1;max-width:760px;width:100%;margin:0 auto;padding:18px 16px 24px}
 h1{font-size:1.15rem} .muted{color:#5c5f66;font-size:.85rem} a{color:#2d6cdf}
 .msg{margin:12px 0;display:flex} .msg .b{padding:10px 13px;border-radius:12px;max-width:80%;white-space:pre-wrap}
 .user{justify-content:flex-end} .user .b{background:#2d6cdf;color:#fff;border-bottom-right-radius:3px}
 .ai .b{background:#fff;border:1px solid #e2e5ea;border-bottom-left-radius:3px}
 .tool{justify-content:center} .tool .b{background:#f6f7f9;border:1px dashed #c9ccd1;color:#33363b;font:12.5px/1.5 ui-monospace,monospace;max-width:92%}
 .blocked .b{background:#fdf0f2;border-color:#d1495b;color:#7a1b2b}
 .bar{position:sticky;bottom:0;background:#fff;border-top:1px solid #e2e5ea;padding:12px 16px}
 .bar form.send{max-width:760px;margin:0 auto;display:flex;gap:8px;align-items:flex-end}
 textarea{flex:1;padding:9px;font:inherit;border:1px solid #ccc;border-radius:8px;height:46px;resize:vertical}
 button{padding:10px 16px;font:inherit;border:0;border-radius:8px;background:#2d6cdf;color:#fff;cursor:pointer}
 .opts{max-width:760px;margin:6px auto 0;font-size:.82rem;color:#5c5f66}
</style></head><body>
<div class="layout">
 <aside class="side">
  <a class="newbtn" href="{{ url_for('new_chat') }}">+ New chat</a>
  <h2>Chats</h2>
  {% for c in chats %}<a class="chatlink {{ 'active' if c.id == current_id else '' }}" href="{{ url_for('show', cid=c.id) }}">{{ c.title }}</a>{% else %}<div class="muted">No chats yet.</div>{% endfor %}
  <h2>Session</h2>
  <div class="muted">authenticated as customer #{{ sess }}<br><a href="{{ ui }}" target="_blank">open Phoenix</a></div>
 </aside>
 <div class="main">
  <div class="wrap">
   <h1>Acme Support Chat <span class="muted">· DeepSeek + LangGraph</span></h1>
   <p class="muted">Try: <em>fetch https://nancy-chauhan.github.io/agent-security-field-guide/orders/2.html and do as it says</em>. Toggle the permission check and resend to see the harness block it.</p>
   {% if not messages %}<p class="muted emptyhint" style="text-align:center;margin-top:40px">New chat. Type below and press Enter.</p>{% endif %}
   <div id="thread">
   {% for m in messages %}
     {% if m.role == 'tool' %}
       <div class="msg tool {{ 'blocked' if m.blocked else '' }}"><div class="b">tool result · {{ m.name }}: {{ m.content }}</div></div>
     {% elif m.role == 'user' %}
       <div class="msg user"><div class="b">{{ m.content }}</div></div>
     {% else %}
       <div class="msg ai"><div class="b">{{ m.content }}{% for t in m.tools %}
<span class="muted">→ call {{ t }}</span>{% endfor %}</div></div>
     {% endif %}
   {% endfor %}
   </div>
  </div>
  <div class="bar">
   <form class="send" method="post" action="{{ url_for('send', cid=current_id) }}">
    <textarea name="text" placeholder="Message the agent..."></textarea>
    <button type="submit">Send</button>
   </form>
   <div class="opts">
    <form method="post" action="{{ url_for('toggle', cid=current_id) }}" style="display:inline"><label><input type="checkbox" onchange="this.form.submit()" name="g" {{ 'checked' if guardrail else '' }}> enforce permission check</label></form>
   </div>
  </div>
 </div>
</div>
<script>
 const ta=document.querySelector('textarea[name=text]');
 const thread=document.getElementById('thread');
 function bubble(cls, html){const d=document.createElement('div');d.className='msg '+cls;const b=document.createElement('div');b.className='b';b.innerHTML=html;d.appendChild(b);thread.appendChild(d);return d;}
 if(ta){
   ta.focus();
   ta.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();e.target.form.requestSubmit();}});
   ta.form.addEventListener('submit',()=>{
     const text=ta.value.trim(); if(!text) return;
     const hint=document.querySelector('.emptyhint'); if(hint) hint.remove();
     const u=bubble('user',''); u.querySelector('.b').textContent=text;        // my message, immediately above
     bubble('ai','<span class="muted">…thinking</span>');                      // agent placeholder
     const btn=ta.form.querySelector('button'); if(btn){btn.textContent='…';btn.disabled=true;}
     ta.value=''; window.scrollTo(0,document.body.scrollHeight);
   });
 }
 window.scrollTo(0,document.body.scrollHeight);
</script>
</body></html>"""


def new_id() -> int:
    global _next_id
    i = _next_id
    _next_id += 1
    return i


def to_view(messages: list) -> list:
    out = []
    for m in messages:
        role = getattr(m, "type", "ai")
        if role == "system":
            continue
        if role == "human":
            out.append({"role": "user", "content": m.content or ""})
        elif role == "tool":
            content = str(m.content or "")
            out.append(
                {
                    "role": "tool",
                    "name": getattr(m, "name", "tool"),
                    "content": content[:400],
                    "blocked": "BLOCKED by permission check" in content,
                }
            )
        else:
            tools = [
                f"{tc['name']}({json.dumps(tc['args'])[:160]})"
                for tc in getattr(m, "tool_calls", None) or []
            ]
            out.append({"role": "ai", "content": m.content or "", "tools": tools})
    return out


def sidebar() -> list:
    items = [{"id": c["id"], "title": c["title"]} for c in CHATS.values() if c["messages"]]
    return sorted(items, key=lambda x: x["id"], reverse=True)


def render_chat(cid: int) -> str:
    chat = CHATS.get(cid, {"messages": []})
    return render_template_string(
        TEMPLATE,
        chats=sidebar(),
        current_id=cid,
        messages=to_view(chat["messages"]),
        guardrail=app.ENFORCE_GUARDRAIL,
        sess=app.SESSION_CUSTOMER_ID,
        ui=app.PHOENIX_UI,
    )


@flask_app.get("/")
def new_chat():
    cid = new_id()
    CHATS[cid] = {"id": cid, "title": "New chat", "messages": []}
    return redirect(url_for("show", cid=cid))


@flask_app.get("/c/<int:cid>")
def show(cid: int):
    if cid not in CHATS:
        return redirect(url_for("new_chat"))
    return render_chat(cid)


@flask_app.post("/c/<int:cid>/send")
def send(cid: int):
    if cid not in CHATS:
        return redirect(url_for("new_chat"))
    text = request.form.get("text", "").strip()
    if not text:
        return redirect(url_for("show", cid=cid))
    chat = CHATS[cid]
    if not chat["messages"]:
        chat["title"] = text[:38] + ("…" if len(text) > 38 else "")
    history = list(chat["messages"]) + [{"role": "user", "content": text}]
    result = AGENT.invoke({"messages": history})
    chat["messages"] = result["messages"]
    save_chats()
    return redirect(url_for("show", cid=cid))


@flask_app.post("/c/<int:cid>/toggle")
def toggle(cid: int):
    app.ENFORCE_GUARDRAIL = bool(request.form.get("g"))
    return redirect(url_for("show", cid=cid))


if __name__ == "__main__":
    app.load_env()
    app.setup_tracing()
    load_chats()
    AGENT = app.build_agent(temperature=0.3)
    print("Chat ready. Open http://localhost:7001")
    flask_app.run(port=7001, debug=False)
