# Glossary

**AI Engineering Bootcamp · BlockseBlock**

Plain-English definitions for every technical term used in this course. Each entry includes an analogy to help the idea stick. Terms are listed alphabetically.

---

## Agent

An AI setup where the model doesn't just answer a single question — it decides what to do next, takes an action, looks at the result, and then decides what to do after that. The model keeps going until the task is done or it gets stuck.

**Analogy:** A travel agent who doesn't just tell you flight options — they actually book the ticket, arrange the hotel, and email you the itinerary, all without you lifting a finger after the first request.

---

## Agent design pattern

A reusable, named architectural solution to a common agent problem. Just as software engineering has patterns like Singleton or Observer, AI agent engineering has named patterns — ReAct, Plan-and-Execute, Reflection, Orchestrator, Human-in-the-Loop — that the community has converged on. Naming a pattern lets teams communicate precisely about architecture choices: "we're using a Plan-and-Execute pattern" instantly describes a whole architecture without explaining every decision.

**Analogy:** Blueprint types in architecture. When an architect says "open-plan loft" or "Victorian terrace", every other architect immediately understands the spatial arrangement, structural decisions, and trade-offs — without seeing the drawing. Agent design patterns do the same for AI system design.

---

## Agent harness

The production scaffolding layer that wraps an agent loop to make it capable of long-running, complex tasks. A harness provides: (1) **planning tools** — explicit task breakdown before execution (e.g., `write_todos`); (2) **virtual filesystem** — persistent memory beyond the context window, with pluggable backends (in-memory, local disk, cloud store); (3) **middleware** — context compression, tool result offloading, subagent context isolation; (4) **subagent delegation** — spawn focused child agents with isolated context. Claude Code, Manus, and Deep Research are all agents running on a harness.

**Analogy:** Scaffolding in construction — the support structure that lets a worker operate safely at height, handling load distribution, safety rails, and material lifts. The worker (agent loop) does the skilled work; the scaffolding (harness) makes it possible to do that work on a tall building.

---

## API (Application Programming Interface)

A defined way for two pieces of software to talk to each other. One program makes a "request" (asking for something), and the other sends back a "response" (the answer). APIs let you use someone else's service — like an LLM — from inside your own application.

**Analogy:** A restaurant menu is an API. You don't go into the kitchen and cook — you place an order (request) using the menu's defined options, and the kitchen sends out a plate (response).

---

## CAG (Cache-Augmented Generation)

An alternative to RAG that skips chunking and retrieval entirely — all documents are loaded into one large context window and the model reads everything at once. No vector database, no retrieval step, zero missed chunks. Works best with fewer than ~50 pages of stable, infrequently-changing documents. Breaks down when documents exceed the context window or change frequently.

**Analogy:** Handing a student the entire textbook before an exam (CAG) vs. giving them a well-organised set of index cards they can search through (RAG). Handing over the book is simpler — if it fits in their bag. For a library of 1,000 books, index cards win.

---

## Chunking

The process of splitting a large document into smaller, overlapping pieces before storing it in a vector database. Models can only process so much text at once (see *Context Window*), so we cut documents into bite-sized pieces that can each fit.

**Analogy:** When you prepare index cards for studying, you don't copy the whole textbook onto one card — you write one idea per card so you can find the right one quickly. Chunking is making those cards.

---

## Context Window

The maximum amount of text (measured in *tokens*) that a model can see and reason about in a single interaction. Text outside the window is invisible to the model — it simply doesn't exist from the model's perspective.

**Analogy:** Imagine you can only read one page of a book at a time, with a piece of paper blocking everything else. Whatever's on that page is your context. If you want the model to know something, it has to be on that page.

---

## Deployment

The process of making your application available to other people, usually by putting it on a server on the internet. A deployed app runs 24/7 without your laptop needing to be open.

**Analogy:** Writing a recipe is development. Cooking it at home and letting your family taste it is testing. Opening a restaurant so strangers can order it is deployment.

---

## Docker

A tool that packages your application and all its dependencies into a self-contained "container" — a lightweight virtual box. Anyone with Docker installed can run your container and get the exact same environment you developed in, regardless of their operating system.

**Analogy:** A shipping container. You load everything your app needs inside it (code, libraries, settings), seal it up, and ship it. Whoever receives it can unpack and run it without worrying about what tools they have installed.

---

## Embedding

A way of converting text (a word, sentence, or whole paragraph) into a list of numbers that captures its meaning. Text with similar meanings will have numbers that are close together, which lets a computer find related content mathematically.

**Analogy:** Imagine plotting cities on a map. London and Paris are close together (geographically similar); London and Tokyo are far apart. Embeddings do the same thing for meaning — "happy" and "joyful" end up near each other; "happy" and "invoice" end up far apart.

---

## Endpoint

A specific URL in your API that performs a specific action. Each endpoint does one thing: `/chat` handles chat messages, `/documents/upload` accepts file uploads, `/health` checks if the server is alive.

**Analogy:** Each department in a company has its own phone extension. The main number is the API; each extension (endpoint) connects you to a different function: sales, support, billing.

---

## Eval Harness

A set of test questions with known correct answers used to measure whether your AI system is working well. You run your app against these questions automatically and check whether the answers are accurate, consistent, and safe. The harness tells you whether a change to your prompt or model made things better or worse — without having to test manually every time.

**Analogy:** A mock exam you run on your AI before trusting it with real users. Just as a student practices with past papers to check they're ready, an eval harness checks your AI's answers against a marking scheme.

---

## Google ADK

Google's Agent Development Kit — an open-source framework for building multi-agent systems with native MCP support. Built for use with Google's Gemini models but provider-agnostic in design. It handles the plumbing of agent communication, tool routing, and state management so you can focus on defining what each agent does.

**Analogy:** A stage manager for a theatre production with multiple actors (agents). Each actor has their own role; the stage manager coordinates who speaks when, hands off props (data), and keeps the whole show running smoothly.

---

## Groq

An inference company — not a model company — that runs open-weight models (Llama, Mixtral, Gemma) on custom LPU (Language Processing Unit) hardware for very fast, low-cost inference. Offers a free tier with no credit card required. Its API is OpenAI-compatible, so any code that works with OpenAI works with Groq by changing one environment variable.

**Analogy:** A sports car rental service that lets you drive models you already know, but on a purpose-built track (LPU hardware) — much faster than a general-purpose road, and the first few laps are free.

---

## Harness engineering

The practice of designing and building the scaffolding layer around an agent loop — choosing what planning tools, memory backends, middleware, and subagent patterns to include for a specific production use case. Features 7–9 of this course build individual harness components from scratch; LangChain's `deepagents` library packages a standard harness out of the box. Key harness engineering decisions: How does the agent break down tasks? What does it remember between steps? When does it spawn a subagent vs. continue in one context? What actions require human approval before execution?

**Analogy:** Deciding which scaffolding system to use for a construction project. A scaffold engineer doesn't just pick the tallest poles — they consider the building shape, load requirements, access points, and how workers will move around. Harness engineering makes the same decisions for AI agent systems.

---

## Health Check

A simple endpoint (usually `GET /health`) that returns "I'm alive and working" when the server is healthy. Monitoring systems ping this endpoint regularly to detect outages automatically.

**Analogy:** The "are you there?" message you send a friend when you haven't heard from them. If they reply, great. If not, something's wrong and you need to investigate.

---

## Human-in-the-Loop (HITL)

A design pattern where the agent pauses before taking a potentially risky or irreversible action and waits for a human to confirm, correct, or approve it. HITL trades automation speed for safety — it's the difference between an agent that drafts an email and one that *sends* it without asking.

**Analogy:** A junior employee who prepares a contract and hands it to their manager for signature before sending it to the client. The junior does the work; the human makes the final call.

---

## Inference Speed

How fast a model generates tokens (roughly: words) per second. Speed matters in real-time applications like voice assistants or chatbots — a slow model feels frustrating to use. Inference speed depends on the model size, the hardware it runs on, and the provider's infrastructure.

**Analogy:** Reading speed for AI. A model that produces 10 tokens per second is like a slow reader who makes you wait for each sentence. A model producing 200 tokens per second feels instant. Groq's LPU hardware is specifically designed to maximise inference speed.

---

## JSON (JavaScript Object Notation)

A text format for representing structured data using curly braces `{}`, square brackets `[]`, colons `:`, and commas `,`. It's the most common format for sending data between web applications and APIs.

**Analogy:** A form you fill out. Fields have names ("First Name:") and values ("Naureen"). JSON is just that form, written in a format computers can read: `{"first_name": "Naureen"}`.

---

## Knowledge Digest

A 2–3 sentence LLM-generated summary of everything a particular tenant or user has asked about across sessions. Built from the *Retrieval Memory* log and injected into the Smart Router's system prompt so the model arrives with context about what the user cares about — without storing entire conversation histories.

**Analogy:** A briefing note a receptionist gives a doctor before a patient walks in: "This patient has asked about knee pain and medication side effects in the last three visits." One paragraph captures the pattern without dumping every conversation verbatim.

---

## LangChain

A Python framework that packages common AI patterns — chains of calls, memory, retrievers, agents — so you don't have to build them from scratch. This course intentionally builds these patterns by hand first so you understand what LangChain is wrapping. Once you understand the fundamentals, LangChain becomes a set of shortcuts rather than a black box.

**Analogy:** A recipe book with pre-made sauces. You could make béchamel from scratch (which this course teaches you to do), or you could buy it in a jar (LangChain). Knowing how to make it means you understand when the jar version is good enough and when you need to cook from scratch.

---

## LangChain Deep Agents (deepagents library)

LangChain's open-source production agent harness (`pip install deepagents`, github.com/langchain-ai/deepagents), built on LangGraph. Provides a complete harness via `create_deep_agent(model=..., tools=[...], system_prompt=...)`, including: a `write_todos` planning tool, a virtual filesystem with pluggable backends (in-memory, local disk, LangGraph Store), middleware stack (context compression, tool result offloading, subagent isolation), and subagent creation. Inspired by Claude Code's architecture. **Not the same as RUC-NLPIR's academic "DeepAgent" paper** — two different projects with confusingly similar names.

**Analogy:** A pre-built scaffolding kit for construction. Instead of welding your own scaffold from raw steel (building harness components from scratch, as in Features 7–9), you assemble a proven, tested kit that already includes all the standard components — safety rails, adjustable legs, platform planks — for most production use cases.

---

## LangGraph

A framework from the LangChain team for building agent workflows as graphs — steps can branch, retry, and loop, not just run linearly. Useful for complex agents that need to make decisions at multiple points, recover from errors, or run sub-tasks in parallel.

**Analogy:** A flowchart vs. a checklist. A checklist (linear chain) is fine for a simple recipe. A flowchart (LangGraph) handles "if the data looks wrong, go back two steps and try a different approach" — it maps out decision points and loops.

---

## LLM (Large Language Model)

A type of AI model trained on enormous amounts of text that can understand and generate human language. It works by predicting the most likely next word (or token) given everything that came before — billions of times, very fast.

**Analogy:** An incredibly well-read person who has absorbed most of the text ever written and can continue any conversation, write any style, and answer most questions — but who sometimes confidently says things that aren't true, so you should always verify important facts.

---

## MCP (Model Context Protocol)

A standard way for AI models to connect to external tools, data sources, and services. Instead of building a custom integration for every tool, MCP provides a shared "plug" that any compatible tool can use to connect to any compatible model.

**Analogy:** The USB standard. Before USB, every device had its own unique plug. USB created one standard connector that works for keyboards, mice, cameras, and phones. MCP is USB for AI tools.

---

## Memory-augmented agent

An agent that persists facts across sessions via explicit storage — writing key information to a memory store after each interaction and reading from it at the start of the next. Unlike the conversation history window (which is short-lived and length-limited), memory storage survives indefinitely and scales across thousands of sessions.

**Analogy:** A doctor who writes patient notes after every appointment and reads them before the next one. Without notes, every appointment starts from scratch. With notes, the doctor already knows your allergies, your history, and what was tried last time.

---

## Modality

The type of input or output a model works with — text, image, audio, or video. A "multimodal" model can handle more than one type. Most LLMs are text-only; multimodal models can read images, listen to audio, or watch video clips alongside text.

**Analogy:** Human senses. Text is reading, audio is hearing, image is seeing. A multimodal AI can do all three — like a friend you can both text and send photos to, and they understand both.

---

## Multi-tenancy

Running one application instance for multiple customers (tenants) where each customer's data, sessions, and documents are completely isolated from every other customer's. Implemented in this course via the `X-Tenant-ID` header — every query is filtered to only touch that tenant's data.

**Analogy:** A shared office building where every company has its own locked suite. They share the same building (infrastructure), but no company can walk into another's office (data isolation). The building manager (your app) enforces the separation.

---

## NFR (Non-Functional Requirement)

A requirement about *how* the system should behave rather than *what* it should do. Examples: "must respond in under 2 seconds", "must handle 1,000 users simultaneously", "must be available 99.9% of the time". These are easy to forget and expensive to add later.

**Analogy:** When you hire a restaurant chef, the job description (cook meals) is the functional requirement. The NFRs are: must wear a hairnet, must wash hands, must not take more than 20 minutes per table. They don't define *what* they cook — they define the *quality standards* around the cooking.

---

## Orchestrator agent

An agent whose job is to break a complex task into subtasks and delegate each subtask to a specialised *subagent*. The orchestrator doesn't do the detailed work itself — it plans, assigns, and synthesises the results. Also called a "planner" or "coordinator" agent in some frameworks.

**Analogy:** A project manager who takes a client brief, splits it into design, copywriting, and dev tasks, assigns each to the right person, and stitches the deliverables together into a final product. The PM doesn't write the code — they orchestrate the people who do.

---

## PageIndex

An alternative retrieval approach by VectifyAI that skips embeddings entirely. Instead of chunking and vector search, it builds a tree of page-level summaries and navigates to the right page using LLM reasoning — the model reads a summary tree, decides which branch to follow, and retrieves specific pages. Achieved 98.7% on FinanceBench. Best for long, structured documents (financial reports, legal contracts, technical manuals) where chunks lose context.

**Analogy:** A book's table of contents + index, used intelligently. Instead of scanning every paragraph (RAG with chunks), you read the chapter summaries, pick the right chapter, then find the right paragraph. The navigation is done by reasoning, not keyword matching.

---

## Parallel tool calling

When the LLM decides to invoke multiple tools simultaneously within a single response, rather than waiting for each result before calling the next. Supported by OpenAI, Groq, and Anthropic. Significantly speeds up agents that need to gather information from multiple sources — e.g., fetch the weather, check the calendar, and look up a contact all at once.

**Analogy:** A research assistant who, instead of checking one database at a time, sends queries to five databases at the same time and waits for all the results before writing the report. Parallel queries, one synthesis.

---

## Plan-and-Execute

An agent design pattern that separates planning from doing. In the first phase, the agent generates a step-by-step plan (without taking any actions). In the second phase, it executes each step in sequence. This improves reliability on complex tasks because the model commits to a structure before it gets distracted by execution details.

**Analogy:** An architect who draws the blueprints first (plan phase), then hands them to the construction crew (execute phase). Designing and building at the same time leads to costly mid-build changes.

---

## Provider

In this course, "provider" means the company or service whose AI models your app calls — for example, OpenAI, Anthropic, Cohere, Groq, or a local SLM via Ollama. The course is designed to be provider-agnostic: you configure your provider in `.env` and all feature code works unchanged regardless of which one you pick.

**Analogy:** A cloud provider for electricity. Whether you're on one utility company or another, your appliances (code) work the same way — you just plug into a different socket (provider) by changing a setting.

---

## RAG (Retrieval-Augmented Generation)

A technique where, before the model generates an answer, the system first searches a database for relevant documents and includes them in the prompt. This grounds the model's answer in real, specific information rather than just its training data.

**Analogy:** Open-book exam vs. closed-book exam. A closed-book LLM answers purely from memory. RAG lets the model take the exam with the textbook open — it searches for the relevant pages first, then writes the answer using what it found.

---

## RUC-NLPIR DeepAgent (research)

An academic research paper and prototype (github.com/RUC-NLPIR/DeepAgent, WWW 2026 Oral, Renmin University + Xiaohongshu) about end-to-end deep reasoning agents. Key contribution: dynamic tool discovery from 16,000+ APIs within a single reasoning stream, with four action types — internal thought, tool search, tool call, and memory fold — and brain-inspired memory (episodic/working/tool). Research-stage prototype, not a production library. Referenced in this course as a frontier callout for where agent architectures are heading. **Not the same as LangChain's `deepagents` library.**

**Analogy:** A research paper describing a new engine design concept vs. a car you can actually buy today. LangChain's `deepagents` is the production car; RUC-NLPIR's DeepAgent is the concept paper showing what engines might look like in five years — fascinating and worth understanding, but not yet in your driveway.

---

## Rate Limiting

A protection mechanism that caps how many requests a user (or your app) can make to an API within a time window. This prevents overuse, abuse, and runaway costs.

**Analogy:** An all-you-can-eat buffet with a rule: you can visit the food stations up to 3 times per 10 minutes. The restaurant still feeds you generously — it just prevents one person from monopolising the food.

---

## ReAct (Reasoning + Acting)

An agent design pattern where the model alternates between *Thought* (reasoning about what to do), *Action* (calling a tool), and *Observation* (reading the tool result) — repeating the loop until the task is done. Each step is visible in the reasoning trace, making the agent's behaviour inspectable and debuggable. Named after the 2022 paper "ReAct: Synergizing Reasoning and Acting in Language Models."

**Analogy:** A detective's notebook. The detective writes down their current theory (Thought), goes to interview a witness (Action), notes what the witness said (Observation), updates their theory, and continues until the case is solved. The notebook lets you follow every step.

---

## Reflection agent

An agent that critiques its own output and revises it until a quality criterion is met. After producing an initial answer, the agent prompts itself (or a separate "critic" model) to identify flaws, then generates a revised answer, looping until the output passes the check. More reliable than a single-pass agent for tasks where correctness matters more than speed.

**Analogy:** A writer who drafts an essay, then reads it as an editor would ("this paragraph is unclear, the conclusion is weak"), rewrites the flagged sections, and repeats until the draft is submission-ready. Self-revision, not just first-draft output.

---

## Retrieval Memory

A persistent log of every query that triggered document retrieval, stored across sessions. Used as the raw material for the *Knowledge Digest* — an LLM summarises the retrieval log into a short paragraph injected into the system prompt, giving the model long-term context about what topics a user cares about.

**Analogy:** Your browser's search history. Every query is logged. A smart assistant reads that history once a week and writes a short note — "this user researches machine learning and tax optimisation" — to inform future sessions.

---

## Session

A period of interaction between a user and the app that is tracked as a continuous conversation. A session has a start (first message) and an end (user closes the window, or the session times out). Session data lets the model remember earlier messages.

**Analogy:** A phone call. Everything said during the call is part of the same session. When you hang up and call back later, the assistant doesn't automatically remember the previous call unless you remind them.

---

## SLM (Small Language Model)

A compact AI model (e.g. Phi-3, Gemma, Mistral) that runs on your own laptop — no internet connection or API key needed. Less capable than frontier LLMs on complex tasks, but free, private, and instant. SLMs are ideal for prototyping, offline environments, and privacy-sensitive use cases. Run them locally using Ollama.

**Analogy:** A pocket calculator vs. a supercomputer — both do maths, just at different scales. The calculator (SLM) fits in your pocket, needs no internet, and solves most everyday problems instantly. The supercomputer (LLM) handles problems the calculator can't, but you need to connect to it remotely.

---

## STT (Speech-to-Text)

Technology that converts spoken audio into written text. The user speaks into a microphone; STT turns the audio waveform into a string of words the AI can process.

**Analogy:** A court stenographer who transcribes everything spoken aloud into a written record. You speak; they type exactly what you said.

---

## Subagent

A specialised agent called by an *orchestrator agent* to complete one specific subtask. A subagent has a narrow scope — it might only know how to search the web, or only how to write code — and reports its result back to the orchestrator. Systems of subagents enable parallel specialisation: each subagent is best-in-class at one thing.

**Analogy:** Specialist consultants called in by a project manager. The PM (orchestrator) runs the project; the structural engineer (subagent A) reviews the foundations, the electrician (subagent B) reviews the wiring. Each is a specialist; none sees the full project.

---

## System Prompt

A special instruction given to the model at the start of every conversation that sets its persona, rules, and purpose. Users don't see the system prompt — it shapes how the model behaves without the user having to repeat instructions every time.

**Analogy:** An employee handbook given to a new hire on their first day. It tells them who the company is, what they're allowed to say, how to handle complaints, and what tone to use. The customer never reads the handbook, but it shapes every interaction they have with that employee.

---

## Temperature

A setting that controls how creative (unpredictable) or focused (predictable) the model's responses are. A temperature of 0 means the model nearly always picks the most likely next word. Higher temperatures increase variety and surprise.

**Analogy:** A dimmer switch for creativity. Turn it down (temperature 0) and you get the same, safe, reliable output every time — like a chef who only makes the house special. Turn it up and the chef starts improvising, which can be brilliant or occasionally weird.

---

## Tenant Isolation

The guarantee that data, sessions, and documents belonging to one *tenant* (customer) are never visible to another. Implemented by filtering every database query with the tenant's ID. Without isolation, a query from customer A could accidentally return customer B's private documents — a serious security and compliance failure.

**Analogy:** Safety deposit boxes at a bank. All boxes sit in the same vault (shared infrastructure). But only you have the key to your box, and the bank enforces that no one else can open it — not even other staff. The vault is shared; the contents are isolated.

---

## Token

The basic unit the model reads and writes. A token is roughly ¾ of a word — "hamburger" might be two tokens ("ham" + "burger"), and a short sentence might be 10–20 tokens. Token counts matter because they determine both the cost of an API call and how much the model can read at once.

**Analogy:** A taxi meter that charges per 0.1 km, not per km. "Km" is a word, but the taxi charges for the smaller unit. Tokens are the taxi's charging unit for language.

---

## Tool Calling

A capability that lets the model "call" functions defined in your code, similar to how a human assistant might say "let me look that up" and go do a web search. The model decides when a tool is needed, formats the call, and the result comes back for the model to use in its reply.

**Analogy:** Giving a research assistant a list of reference books and saying "you may use these". When they don't know something, they pull the right book, find the answer, and incorporate it. You define which books (tools) exist; the assistant decides when to use them.

---

## Tool-augmented RAG

A hybrid pattern that combines semantic retrieval with live tool calls. The system does a vector search for relevant document chunks *and* calls external APIs (weather, database, calendar) within the same agent loop. The model synthesises static document knowledge with real-time data in a single response. More powerful than either RAG or tool calling alone.

**Analogy:** A financial advisor who both reads your portfolio documents (RAG) and calls a live stock price API (tool) before making a recommendation. The advice is grounded in your history and in today's market — not just one or the other.

---

## TTS (Text-to-Speech)

Technology that converts written text into spoken audio. The app sends a string of text; TTS turns it into a human-sounding voice recording that plays in the browser.

**Analogy:** An audiobook narrator who reads any text you give them aloud. You provide the script; they provide the voice.

---

## Vector Database

A specialised database designed to store and search *embeddings* (see *Embedding*). Instead of searching by exact keyword match, a vector database finds items by semantic similarity — it can find documents that *mean* the same thing as your query, even if they use different words.

**Analogy:** A library where books are arranged by topic rather than title. You don't need to know the exact book name — you describe what you're looking for ("something about managing grief") and the librarian points you to the relevant shelf. The arrangement is by meaning, not alphabet.

---

## VLM (Vision Language Model)

A model that understands images AND text together. You send a photo and a question; the model answers about what it sees. Examples include LLaVA (runs locally via Ollama), Phi-3 Vision, and GPT-4V. VLMs enable features like "describe this product photo", "what's wrong in this screenshot", or "read the text in this image".

**Analogy:** The difference between a friend who only reads your texts vs. one who can also look at the photo you send them. A VLM is the friend who can do both — they read your question and look at your image before replying.
