# ruff: noqa: E501
"""A free-form chat window for the Acme support agent, traced to Phoenix.

Type anything (e.g. "fetch https://... and do as it says"). The agent keeps conversation
history and can fetch pages, look up customers/orders, and send reports. Every tool call and
result is shown inline, and every turn is a trace in Phoenix. Toggle the permission check to
watch the harness block out-of-scope customer access and external sends.

Run:  demo-venv/bin/python chat.py   then open http://localhost:7001
"""

from __future__ import annotations

import json

import app  # reuse tools, agent builder, tracing, env
from flask import Flask, redirect, render_template_string, request, url_for

CONVO: list = []  # LangChain message objects for the running conversation

flask_app = Flask(__name__)
AGENT = None

TEMPLATE = """<!doctype html><html><head><meta charset="utf-8"><title>Acme Support Chat</title>
<style>
 body{font:15px/1.6 system-ui,sans-serif;margin:0;color:#1b1b1f;background:#f3f4f6}
 .wrap{max-width:760px;margin:0 auto;padding:18px 16px 140px}
 h1{font-size:1.2rem} .muted{color:#5c5f66;font-size:.85rem}
 .msg{margin:12px 0;display:flex} .msg .b{padding:10px 13px;border-radius:12px;max-width:80%;white-space:pre-wrap}
 .user{justify-content:flex-end} .user .b{background:#2d6cdf;color:#fff;border-bottom-right-radius:3px}
 .ai .b{background:#fff;border:1px solid #e2e5ea;border-bottom-left-radius:3px}
 .tool{justify-content:center} .tool .b{background:#f6f7f9;border:1px dashed #c9ccd1;color:#33363b;font:12.5px/1.5 ui-monospace,monospace;max-width:92%}
 .blocked .b{background:#fdf0f2;border-color:#d1495b;color:#7a1b2b}
 .bar{position:fixed;bottom:0;left:0;right:0;background:#fff;border-top:1px solid #e2e5ea;padding:12px 16px}
 .bar form{max-width:760px;margin:0 auto;display:flex;gap:8px;align-items:center}
 textarea{flex:1;padding:9px;font:inherit;border:1px solid #ccc;border-radius:8px;height:46px;resize:vertical}
 button{padding:10px 16px;font:inherit;border:0;border-radius:8px;background:#2d6cdf;color:#fff;cursor:pointer}
 .opts{max-width:760px;margin:6px auto 0;font-size:.82rem;color:#5c5f66} a{color:#2d6cdf}
</style></head><body>
<div class="wrap">
 <h1>Acme Support Chat <span class="muted">· DeepSeek + LangGraph · session = customer #{{ sess }} · <a href="{{ ui }}" target="_blank">Phoenix</a></span></h1>
 <p class="muted">Try: <em>fetch https://nancy-chauhan.github.io/agent-security-field-guide/orders/9.html and do as it says</em>. Toggle the permission check below and resend to see the harness block it.</p>
 {% if not messages %}<p class="muted" style="text-align:center;margin-top:48px">No messages yet. Type below and press Enter. The agent may take a few seconds while it calls tools.</p>{% endif %}
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
<div class="bar">
 <form method="post" action="{{ url_for('send') }}">
  <textarea name="text" placeholder="Message the agent...">{{ draft }}</textarea>
  <button type="submit">Send</button>
 </form>
 <div class="opts">
  <form method="post" action="{{ url_for('toggle') }}" style="display:inline"><label><input type="checkbox" onchange="this.form.submit()" name="g" {{ 'checked' if guardrail else '' }}> enforce permission check</label></form>
  · <a href="{{ url_for('reset') }}">reset conversation</a>
 </div>
</div>
<script>
 const ta=document.querySelector('textarea[name=text]');
 if(ta){ta.focus();ta.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();e.target.form.requestSubmit();}});}
 const sendForm=ta?ta.form:null;
 if(sendForm){sendForm.addEventListener('submit',()=>{const b=sendForm.querySelector('button');if(b){b.textContent='…';b.disabled=true;}});}
 window.scrollTo(0,document.body.scrollHeight);
</script>
</body></html>"""


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


def page(draft: str = "") -> str:
    return render_template_string(
        TEMPLATE,
        messages=to_view(CONVO),
        draft=draft,
        guardrail=app.ENFORCE_GUARDRAIL,
        sess=app.SESSION_CUSTOMER_ID,
        ui=app.PHOENIX_UI,
    )


@flask_app.get("/")
def index() -> str:
    return page()


@flask_app.post("/send")
def send():
    global CONVO
    text = request.form.get("text", "").strip()
    if not text:
        return redirect(url_for("index"))
    history = list(CONVO) + [{"role": "user", "content": text}]
    result = AGENT.invoke({"messages": history})
    CONVO = result["messages"]
    return redirect(url_for("index"))


@flask_app.post("/toggle")
def toggle():
    app.ENFORCE_GUARDRAIL = bool(request.form.get("g"))
    return redirect(url_for("index"))


@flask_app.get("/reset")
def reset():
    global CONVO
    CONVO = []
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.load_env()
    app.setup_tracing()
    AGENT = app.build_agent(temperature=0.3)
    print("Chat ready. Open http://localhost:7001")
    flask_app.run(port=7001, debug=False)
