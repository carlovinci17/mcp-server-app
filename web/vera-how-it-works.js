      // Steps 1, 2, 5, 6 are identical no matter which tool gets called - only
      // step 3 (tool choice) and step 4 (retrieval) actually differ per path,
      // exactly mirroring the real code: chat.py/chat_service.py don't know or
      // care which tool the agent picked, only the tool/service layer differs.
      const RETRIEVAL_BY_KIND = {
        exact: {
          toolLine: '-> selects get_department_contacts',
          title: 'Retrieval — exact lookup',
          plainText:
            'A single, direct database query by ID or a simple filter. No text matching involved at all - the fastest, most deterministic path.',
          techText:
            'get_department_contacts(department="Design")\nsrc/services/employee_service.py\nSQLAlchemy: SELECT * FROM employees\n  WHERE department = :department\nNo embeddings, no ranking',
        },
        substring: {
          toolLine: '-> selects search_documents',
          title: 'Retrieval — SQL substring search',
          plainText:
            'A fuzzy but literal text match against the title and department columns only. Finds partial matches, but has no concept of meaning or synonyms - and no embeddings are involved.',
          techText:
            "search_documents(query=\"onboarding\")\nsrc/services/document_service.py\nAzure SQL via SQLAlchemy:\nWHERE title ILIKE '%onboarding%'\n  OR department ILIKE '%onboarding%'\nNote: the tool's own docstring also\nmentions \"tags\", but that column is\nnot actually queried",
        },
        vector: {
          toolLine: '-> selects global_search',
          title: 'Retrieval — vector / hybrid RAG',
          plainText:
            'The question is embedded into a vector, then Azure AI Search runs <a class="doc-link" href="https://learn.microsoft.com/en-us/azure/search/index-similarity-and-scoring" target="_blank" rel="noopener">BM25</a> keyword search and <a class="doc-link" href="https://learn.microsoft.com/en-us/azure/search/vector-search-ranking" target="_blank" rel="noopener">HNSW</a> vector search together in one query and fuses the two rankings automatically.',
          techText:
            'global_search(query="remote work policy")\nsrc/services/search_service.py\nembed_text() -> Azure OpenAI\n  text-embedding-3-small (1536-dim)\nAzure AI Search .search() called with\nboth search_text= (BM25) and\nvector_queries= (HNSW) -> automatic\nhybrid fusion, single round trip',
        },
      };

      function buildStepData(kind) {
        const retrieval = RETRIEVAL_BY_KIND[kind];
        return [
          {
            title: 'Prompt sent',
            plainText:
              'Your message is submitted to the backend, which validates it and hands off to the agent service. No auth token needed - this endpoint is intentionally anonymous.',
            techText:
              'POST /api/chat\nContent-Type: application/json\nbody: {message, previous_response_id}\nsrc/tools/chat.py: _start_chat()\nResponse: {response_id, status:"queued"}\nHTTP 200',
            showAgent: false,
          },
          {
            title: 'Async kickoff',
            plainText:
              "This is the one and only LLM call for the whole turn: the Azure AI Foundry agent run starts in the background and returns a job ID right away instead of blocking - built specifically to dodge Static Web Apps' hard ~45s request timeout. No icon yet because the backend can't see what the model decided until it polls.",
            techText:
              'client.responses.create(\n  background=True, store=True)\nsrc/services/chat_service.py\nReturns immediately: status="queued"\n(single API call for this whole turn)',
            showAgent: false,
          },
          {
            title: 'Tool choice',
            plainText:
              'The agent itself decides whether this needs a tool at all, and which one - not fixed application logic. This is the same call from step 2, now polled mid-flight; nothing new is sent to the model here.',
            techText: `Same run as step 2, polled via\nresponses.retrieve(id)\n23 MCP tools available:\ndocuments(6) policies(3) meetings(3)\nemployees(3) customers(3) search(3)\nhealth(2)\n${retrieval.toolLine}`,
            showAgent: true,
          },
          {
            title: retrieval.title,
            plainText: retrieval.plainText,
            techText: retrieval.techText,
            showAgent: false,
          },
          {
            title: 'Synthesis',
            plainText:
              'The agent composes a natural-language answer from whatever the tool returned. Still the same single call from step 2 - just polled again once it reaches its terminal status.',
            techText:
              'Same agent run, no extra call\nsrc/services/chat_service.py\nresponses.retrieve(id) -> _to_job_status()\nstatus: "completed"\nreply = response.output_text',
            showAgent: true,
          },
          {
            title: 'Reply',
            plainText:
              'The browser, which has been polling in the background, receives the finished reply and renders it - plus a pill showing which tool was actually used.',
            techText:
              'GET /api/chat/status?id=...\n(polled ~every 1.5s by the browser)\nmcp_call items de-duped by name\nmarked.parse() -> DOMPurify.sanitize()',
            showAgent: false,
          },
        ];
      }

      let state = {
        selected: null,
        doneUpTo: 0,
        activeStep: 0,
        playing: false,
        timers: [],
      };
      const reducedMotion =
        window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;

      function stageState(n) {
        if (state.activeStep === n) return 'active';
        if (state.doneUpTo >= n) return 'done';
        return 'pending';
      }

      function renderSteps() {
        const container = document.getElementById('stepsContainer');
        container.innerHTML = '';
        if (!state.selected) return;
        const stepData = buildStepData(state.selected);
        stepData.forEach((step, idx) => {
          const n = idx + 1;
          const st = stageState(n);
          const card = document.createElement('div');
          card.className = `step-card ${st}`;
          card.innerHTML = `
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;align-items:start;">
          <div style="display:flex;flex-direction:column;gap:6px;">
            <div style="display:flex;align-items:center;gap:10px;">
              <div class="step-badge">${st === 'done' ? '✓' : n}</div>
              <div style="font-size:16px;font-weight:600;color:var(--text-primary);">${step.title}</div>
              ${
                step.showAgent
                  ? `<svg width="18" height="18" viewBox="0 0 48 48" style="flex-shrink:0;">
                <rect x="8" y="8" width="32" height="33" rx="12" fill="${st === 'pending' ? '#c7cdd6' : 'var(--accent)'}"></rect>
                <rect x="12.5" y="19" width="23" height="17.5" rx="7.5" fill="#081026"></rect>
                <rect x="18" y="23.5" width="4.2" height="8.6" rx="2.1" fill="${st === 'pending' ? '#454b66' : '#5eead4'}"></rect>
                <rect x="25.8" y="23.5" width="4.2" height="8.6" rx="2.1" fill="${st === 'pending' ? '#454b66' : '#5eead4'}"></rect>
              </svg>`
                  : ''
              }
            </div>
            <div style="font-size:13px;color:var(--text-body);line-height:1.5;font-weight:500;">${step.plainText}</div>
          </div>
          <div style="display:flex;flex-direction:column;gap:4px;text-align:left;background:var(--surface-main);border-radius:8px;padding:12px;border-left:3px solid var(--accent);">
            <div style="font-size:11px;font-family:'IBM Plex Mono',monospace;color:var(--text-body);line-height:1.7;font-weight:500;white-space:pre-line;">${step.techText}</div>
          </div>
        </div>
      `;
          container.appendChild(card);
        });
      }

      function durationFor(n) {
        if (reducedMotion) return 450;
        return [900, 1100, 1200, 2200, 1000, 1400][n - 1] || 900;
      }

      function advance(n) {
        const stepData = buildStepData(state.selected);
        if (n > stepData.length) {
          state.playing = false;
          state.activeStep = 0;
          state.doneUpTo = stepData.length;
          renderSteps();
          return;
        }
        state.activeStep = n;
        state.playing = true;
        renderSteps();
        const dur = durationFor(n);
        const timer = setTimeout(() => {
          state.doneUpTo = n;
          state.activeStep = 0;
          renderSteps();
          advance(n + 1);
        }, dur);
        state.timers.push(timer);
      }

      function startExample(key) {
        state.timers.forEach(clearTimeout);
        state.timers = [];
        state.selected = key;
        state.doneUpTo = 0;
        state.activeStep = 0;
        state.playing = true;
        renderSteps();
        const timer = setTimeout(() => advance(1), 300);
        state.timers.push(timer);
      }

      function updateButtonStyles() {
        const exactBtn = document.getElementById('exactBtn');
        const substringBtn = document.getElementById('substringBtn');
        const vectorBtn = document.getElementById('vectorBtn');

        exactBtn.style.background =
          state.selected === 'exact'
            ? 'var(--info-blue-tint-bg)'
            : 'var(--surface-raised)';
        exactBtn.style.borderColor =
          state.selected === 'exact'
            ? 'var(--info-blue)'
            : 'var(--border-subtle)';

        substringBtn.style.background =
          state.selected === 'substring'
            ? 'var(--pending-tint-bg)'
            : 'var(--surface-raised)';
        substringBtn.style.borderColor =
          state.selected === 'substring'
            ? 'var(--pending-text)'
            : 'var(--border-subtle)';

        vectorBtn.style.background =
          state.selected === 'vector'
            ? 'var(--success-tint-bg)'
            : 'var(--surface-raised)';
        vectorBtn.style.borderColor =
          state.selected === 'vector'
            ? 'var(--success-text)'
            : 'var(--border-subtle)';
      }

      function resetAll() {
        state.timers.forEach(clearTimeout);
        state = {
          selected: null,
          doneUpTo: 0,
          activeStep: 0,
          playing: false,
          timers: [],
        };
        updateButtonStyles();
        renderSteps();
      }

      document.getElementById('exactBtn').addEventListener('click', () => {
        startExample('exact');
        updateButtonStyles();
      });
      document.getElementById('substringBtn').addEventListener('click', () => {
        startExample('substring');
        updateButtonStyles();
      });
      document.getElementById('vectorBtn').addEventListener('click', () => {
        startExample('vector');
        updateButtonStyles();
      });
      document.getElementById('resetBtn').addEventListener('click', resetAll);

      // Mirrors src/tools/health.py's _CAPABILITIES / _TOOL_DESCRIPTIONS
      // (same source of truth as the app's own "MCP Server Tools" popup).
      const TOOL_CATEGORY_COLORS = {
        documents: 'var(--info-blue)',
        policies: 'var(--pending-text)',
        meetings: 'var(--success-text)',
        employees: '#8b5cf6',
        customers: '#dc2626',
        search: 'var(--accent)',
        health: 'var(--text-secondary)',
      };
      const ALL_TOOL_GROUPS = [
        {
          category: 'documents',
          label: 'Documents',
          tools: [
            [
              'search_documents',
              'Search documents, policies, meeting notes, and project docs.',
            ],
            [
              'list_documents',
              'List documents, optionally filtered by type or department.',
            ],
            [
              'get_document',
              "Retrieve a document's full content and metadata by ID.",
            ],
            [
              'get_document_metadata',
              "Retrieve a document's metadata without its full content.",
            ],
            [
              'find_related_documents',
              'Find documents related to a given document ID.',
            ],
            [
              'summarize_document',
              "Retrieve a document's content for summarization.",
            ],
          ],
        },
        {
          category: 'policies',
          label: 'Policies',
          tools: [
            [
              'search_policies',
              'Search company policies by title or department.',
            ],
            [
              'list_policies',
              'List company policies, optionally filtered by department.',
            ],
            [
              'get_policy',
              "Retrieve a company policy's full content and metadata.",
            ],
          ],
        },
        {
          category: 'meetings',
          label: 'Meetings',
          tools: [
            ['search_meetings', 'Search meeting notes by title or department.'],
            [
              'list_meetings',
              'List meeting notes, optionally filtered by department.',
            ],
            [
              'summarize_meeting',
              "Retrieve a meeting note's content for summarization.",
            ],
          ],
        },
        {
          category: 'employees',
          label: 'Employees',
          tools: [
            [
              'find_employee',
              'Find employees by name, email, department, or title.',
            ],
            [
              'list_departments',
              'List all departments and their employee counts.',
            ],
            [
              'get_department_contacts',
              'List all employees in a given department.',
            ],
          ],
        },
        {
          category: 'customers',
          label: 'Customers',
          tools: [
            [
              'search_customers',
              'Search customers by name, industry, or region.',
            ],
            ['get_customer', "Retrieve a customer's details by ID."],
            [
              'list_customers',
              'List customers, optionally filtered by status.',
            ],
          ],
        },
        {
          category: 'search',
          label: 'Search',
          tools: [
            [
              'keyword_search',
              'Full-text <a class="doc-link" href="https://learn.microsoft.com/en-us/azure/search/index-similarity-and-scoring" target="_blank" rel="noopener">BM25</a> keyword search across all indexed content.',
            ],
            [
              'semantic_search',
              'Vector-only similarity search for conceptual or natural-language queries.',
            ],
            [
              'global_search',
              'Hybrid <a class="doc-link" href="https://learn.microsoft.com/en-us/azure/search/index-similarity-and-scoring" target="_blank" rel="noopener">BM25</a> + vector search across all indexed content.',
            ],
          ],
        },
        {
          category: 'health',
          label: 'Health',
          tools: [
            [
              'server_health',
              'Report server health and Azure dependency connectivity.',
            ],
            [
              'list_capabilities',
              'List all MCP tool categories and their tools.',
            ],
          ],
        },
      ];

      function renderAllTools() {
        const grid = document.getElementById('allToolsGrid');
        if (!grid) return;
        grid.innerHTML = ALL_TOOL_GROUPS.map((group) => {
          const color = TOOL_CATEGORY_COLORS[group.category];
          const items = group.tools
            .map(
              ([name, desc]) => `
                <div>
                  <div style="font-family: 'IBM Plex Mono', monospace; font-size: 12px; font-weight: 600; color: var(--text-primary);">${name}</div>
                  <div style="font-size: 12px; color: var(--text-secondary); margin-top: 1px; line-height: 1.5;">${desc}</div>
                </div>`,
            )
            .join('');
          return `
            <div style="border-left: 3px solid ${color}; padding-left: 12px;">
              <div style="font-size: 12.5px; font-weight: 600; color: ${color};">${group.label} (${group.tools.length})</div>
              <div class="tool-items-grid">
                ${items}
              </div>
            </div>`;
        }).join('');
      }

      // Sidebar tab switching
      const navButtons = document.querySelectorAll('.howitworks-nav-btn');
      const panels = document.querySelectorAll('.panel');
      navButtons.forEach((btn) => {
        btn.addEventListener('click', () => {
          const target = btn.getAttribute('data-panel');
          navButtons.forEach((b) => b.classList.toggle('active', b === btn));
          panels.forEach((p) =>
            p.classList.toggle('active', p.id === `panel-${target}`),
          );
        });
      });

      renderAllTools();
      renderSteps();
