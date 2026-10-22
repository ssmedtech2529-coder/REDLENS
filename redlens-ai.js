/**
 * Red Lens AI Assistant & Chatbot Interface
 * Provides biomedical educational guidance, report interpretation, and interactive chat.
 * Integrates directly with RedLensAPI service.
 */

(function () {
  "use strict";

  const ID_KEYS = /^(pid|patientid|name|pname|phone|pph|village|pvil|location|centre|center|pcen|operator|by|pby|address|id|email|contact)$/i;
  const QUESTIONS = [
    "What is anemia?",
    "What are the common symptoms of anemia?",
    "What causes low hemoglobin?",
    "Which foods contain iron?",
    "How does the Red Lens system work?",
    "How does the MAX30102 sensor work?",
    "What does my screening report mean?",
    "Why is a laboratory Hb test important?",
    "What are the limitations of AI-based anemia screening?",
    "How can I understand my screening results?"
  ];

  let history = [];
  let context = null;
  let lang = "en";
  let lastMsg = null;
  let busy = false;

  // Sanitizer: drop identifying keys and base64 images before data leaves browser
  function cleanContext(obj) {
    if (Array.isArray(obj)) return obj.map(cleanContext);
    if (obj && typeof obj === "object") {
      const clean = {};
      for (const k in obj) {
        if (!ID_KEYS.test(k)) {
          clean[k] = cleanContext(obj[k]);
        }
      }
      return clean;
    }
    return typeof obj === "string" && (obj.startsWith("data:") || obj.length > 300)
      ? null
      : obj;
  }

  const css = `
  #t-ai .chat {
    display: flex;
    flex-direction: column;
    height: 70vh;
    min-height: 420px;
  }
  #aiLog {
    flex: 1;
    overflow-y: auto;
    background: #f8fafc;
    border: 1.5px solid var(--line, #d9e2e8);
    border-radius: 12px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .bub {
    max-width: 82%;
    padding: 10px 14px;
    border-radius: 16px;
    white-space: pre-wrap;
    word-wrap: break-word;
    font-size: 14px;
    line-height: 1.5;
    animation: fadeIn 0.2s ease-in-out;
  }
  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
  }
  .bub.u {
    background: var(--pri, #0f5c7a);
    color: #fff;
    margin-left: auto;
    border-bottom-right-radius: 4px;
    box-shadow: 0 2px 4px rgba(15,92,122,0.15);
  }
  .bub.a {
    background: #ffffff;
    border: 1px solid var(--line, #d9e2e8);
    color: var(--ink, #16222b);
    border-bottom-left-radius: 4px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.04);
  }
  .bub.err {
    background: #fde8e6;
    color: #b42318;
    border: 1.5px solid #fecdca;
  }
  .typing-indicator {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 10px 16px;
  }
  .typing-dot {
    width: 6px;
    height: 6px;
    background: #5d6b76;
    border-radius: 50%;
    animation: pulse 1.2s infinite ease-in-out;
  }
  .typing-dot:nth-child(2) { animation-delay: 0.2s; }
  .typing-dot:nth-child(3) { animation-delay: 0.4s; }
  @keyframes pulse {
    0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
    40% { transform: scale(1.1); opacity: 1; }
  }
  .qs {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 10px 0;
  }
  .qs button {
    font-size: 12px;
    padding: 6px 12px;
    margin: 0;
    border-radius: 20px;
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    color: #334155;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .qs button:hover {
    background: #e2e8f0;
    border-color: #94a3b8;
  }
  .inp {
    display: flex;
    gap: 8px;
    margin-top: 8px;
  }
  .inp input {
    margin: 0;
    flex: 1;
  }
  .inp .btn {
    margin: 0;
    white-space: nowrap;
  }
  .ctxbox {
    font-size: 13px;
    background: #e6f1f5;
    border-left: 4px solid var(--pri, #0f5c7a);
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .ctxbox .clear-ctx {
    background: none;
    border: none;
    color: #0a4258;
    text-decoration: underline;
    cursor: pointer;
    font-size: 12px;
  }`;

  function initUI() {
    const nav = document.querySelector("#nav");
    const main = document.querySelector("main");
    if (!nav || !main) {
      setTimeout(initUI, 100);
      return;
    }

    if (document.querySelector("#t-ai")) return; // already initialized

    document.head.appendChild(
      Object.assign(document.createElement("style"), { textContent: css })
    );

    // AI Tab Button in Header Nav
    const tabBtn = Object.assign(document.createElement("button"), {
      textContent: "AI Assistant"
    });
    tabBtn.dataset.t = "ai";
    tabBtn.id = "btn-tab-ai";
    nav.appendChild(tabBtn);

    // AI Tab Section
    const sec = document.createElement("section");
    sec.id = "t-ai";
    sec.className = "tab";
    sec.innerHTML = `
      <div class="card">
        <div class="row" style="justify-content:space-between; align-items:center; margin-bottom:8px">
          <div style="display:flex; align-items:center; gap:8px">
            <h2 style="margin:0">Red Lens AI Assistant</h2>
            <span class="badge" style="background:#e0f2fe; color:#0284c7; font-size:11px">Clinical Support Agent</span>
          </div>
          <span id="aiStat" class="badge na">Checking backend…</span>
        </div>
        <p class="msg" style="margin-top:0">
          Provides evidence-based educational support, physiological interpretation of sensor readings, and plain-English screening summaries.
          <b>Does not replace a laboratory diagnosis.</b>
        </p>
        <div id="aiCtx" class="ctxbox" style="display:none">
          <span id="aiCtxText">Report context attached.</span>
          <button class="clear-ctx" id="aiClearCtx">Detach report</button>
        </div>
        <div class="chat">
          <div id="aiLog"></div>
          <div class="qs" id="aiQs"></div>
          <div class="inp">
            <input id="aiIn" maxlength="1500" placeholder="Ask about anemia, nutrition, MAX30102, or your report…" autocomplete="off">
            <button class="btn p" id="aiSend">Send</button>
          </div>
          <div class="row" style="margin-top:8px; justify-content:space-between">
            <div style="display:flex; gap:12px; align-items:center">
              <label style="display:flex; align-items:center; gap:6px; margin:0; font-size:12px">
                Language
                <select id="aiLang" style="width:auto; margin:0; padding:4px 8px; font-size:12px">
                  <option value="en">English</option>
                  <option value="ta">தமிழ் (Tamil)</option>
                </select>
              </label>
            </div>
            <div style="display:flex; gap:6px">
              <button class="btn" id="aiRetry" style="display:none">Retry</button>
              <button class="btn d" id="aiClear">Clear Chat</button>
            </div>
          </div>
        </div>
      </div>
    `;
    main.appendChild(sec);

    const $ = (s) => document.querySelector(s);

    function showTab(id) {
      document.querySelectorAll("#nav button").forEach((b) =>
        b.classList.toggle("on", b.dataset.t === id)
      );
      document.querySelectorAll(".tab").forEach((t) =>
        t.classList.toggle("on", t.id === "t-" + id)
      );
      window.scrollTo({ top: 0 });
    }
    tabBtn.onclick = () => showTab("ai");

    function bubble(text, cls) {
      const log = $("#aiLog");
      const d = document.createElement("div");
      d.className = "bub " + cls;
      d.textContent = text;
      log.appendChild(d);
      log.scrollTop = log.scrollHeight;
      return d;
    }

    function showTypingIndicator() {
      const log = $("#aiLog");
      const d = document.createElement("div");
      d.className = "bub a typing-indicator";
      d.innerHTML = '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';
      log.appendChild(d);
      log.scrollTop = log.scrollHeight;
      return d;
    }

    function greet() {
      bubble(
        "Hello! I am Red Lens AI Assistant. I can explain anemia screening results, " +
        "correlate hemoglobin sensor readings with image analysis, and answer nutritional or symptom questions.\n\n" +
        "Note: I am an educational support tool and cannot provide a medical diagnosis. A laboratory blood test (CBC) is required for clinical confirmation.",
        "a"
      );
    }

    async function checkBackendStatus() {
      const s = $("#aiStat");
      if (!window.RedLensAPI) {
        s.className = "badge bad";
        s.textContent = "API Service Missing";
        return;
      }
      try {
        const health = await window.RedLensAPI.checkHealth();
        if (health.ai_mode === "ai") {
          s.className = "badge ok";
          s.textContent = `AI Online (${health.active_model || "GPT-4o-mini"})`;
        } else {
          s.className = "badge sim";
          s.textContent = "DEMO Mode (Rules Engine)";
        }
      } catch (err) {
        s.className = "badge bad";
        s.textContent = "Backend Offline";
      }
    }

    async function send(text) {
      if (busy || !text || !text.trim()) return;
      busy = true;
      lastMsg = text.trim();
      $("#aiRetry").style.display = "none";

      bubble(text, "u");
      $("#aiIn").value = "";

      const typing = showTypingIndicator();

      try {
        if (!window.RedLensAPI) {
          throw new Error("RedLensAPI service is not initialized.");
        }
        const data = await window.RedLensAPI.sendChat(text, history, lang, context);
        typing.remove();

        history.push(
          { role: "user", content: text },
          { role: "assistant", content: data.reply }
        );
        bubble(data.reply, "a");
      } catch (err) {
        typing.remove();
        const errMsg = err.message || "Failed to reach AI service.";
        bubble(
          err.status === 502
            ? `AI Service Notice: ${errMsg}`
            : `Connection Notice: ${errMsg}`,
          "err"
        );
        $("#aiRetry").style.display = "inline-block";
      } finally {
        busy = false;
        checkBackendStatus();
      }
    }

    // Populate suggested questions
    const qsBox = $("#aiQs");
    QUESTIONS.forEach((q) => {
      const b = document.createElement("button");
      b.textContent = q;
      b.onclick = () => send(q);
      qsBox.appendChild(b);
    });

    $("#aiSend").onclick = () => send($("#aiIn").value);
    $("#aiIn").addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        send($("#aiIn").value);
      }
    });

    $("#aiLang").onchange = (e) => (lang = e.target.value);
    $("#aiRetry").onclick = () => {
      document.querySelector("#aiLog .bub.err:last-child")?.remove();
      send(lastMsg);
    };
    $("#aiClear").onclick = () => {
      history = [];
      $("#aiLog").innerHTML = "";
      greet();
    };
    $("#aiClearCtx").onclick = () => {
      context = null;
      $("#aiCtx").style.display = "none";
    };

    // Attach "Ask AI About This Report" on Result page
    function attachAskButton() {
      const printBtn = document.querySelector("#resPrint");
      if (printBtn && !document.querySelector("#btnAskAI")) {
        const ask = Object.assign(document.createElement("button"), {
          id: "btnAskAI",
          className: "btn p",
          textContent: "Ask AI About This Report"
        });
        printBtn.parentNode.insertBefore(ask, printBtn);
        ask.onclick = () => {
          // Check current active screening state in global S, or fetch latest saved record
          let activeRec = (window.S && window.S.rec) ? window.S.rec : null;
          if (!activeRec) {
            try {
              const recs = JSON.parse(localStorage.getItem("anemiascan.records.v2")) || [];
              if (recs.length > 0) activeRec = recs[0];
            } catch (e) {}
          }

          if (!activeRec) {
            alert("Please save or complete a screening result first, then ask AI about the report.");
            return;
          }

          context = cleanContext(activeRec);
          $("#aiCtx").style.display = "flex";
          $("#aiCtxText").textContent =
            `Report loaded for ${activeRec.gender || "patient"} (Age: ${activeRec.age || "N/A"}, Hb: ${activeRec.hb != null ? activeRec.hb + " g/dL" : "Not measured"}).`;
          showTab("ai");
          send("Please explain this screening report in simple language, interpret the readings, and outline next steps.");
        };
      }
    }

    attachAskButton();
    greet();
    checkBackendStatus();

    // Recheck status when RedLensAPI emits changes
    if (window.RedLensAPI) {
      window.RedLensAPI.onStatusChange = () => checkBackendStatus();
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initUI);
  } else {
    initUI();
  }
})();
