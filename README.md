
<div align="center">
  <!-- title -->
  <a href="https://git.io/typing-svg">
    <picture>
      <source media="(prefers-color-scheme: dark)"
        srcset="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&pause=1000&speed=40&color=58A6FF&width=700&height=50&center=true&lines=Hi%2C+I%27m+konlue.+Walking+in+AI+Full-Stack.&repeat=false&loop=false" />
      <img src="https://readme-typing-svg.demolab.com?font=Fira+Code&weight=600&size=24&pause=1000&speed=40&color=0969DA&width=700&height=50&center=true&lines=Hi%2C+I%27m+konlue.+Walking+in+AI+Full-Stack.&repeat=false&loop=false" alt="Typing SVG" />
    </picture>
  </a>
</div>
</br>
<div align="center">
  <!-- Links -->
  <img src="https://api.iconify.design/mdi:gmail.svg?color=%23EA4335&width=20&height=20" width="20" height="20" align="absmiddle" />
  <a href="mailto:yuxiaoyu.dev@gmail.com"><b>yuxiaoyu.dev@gmail.com</b></a>
  &nbsp;&nbsp;·&nbsp;&nbsp;
  <img src="https://api.iconify.design/mdi:post-outline.svg?color=%232E7D32&width=20&height=20" width="20" height="20" align="absmiddle" />
  <a href="https://konlue.github.io" target="_blank" rel="noopener"><b>https://konlue.github.io</b></a>
</div>
</br>

<h2 align="left">Contributing to</h2>

### [apache/shenyu](https://github.com/apache/shenyu)

> **Apache ShenYu** (⭐ 8.9k) — Java-native API gateway for service proxy, protocol conversion and API governance.

**What I did**: Bug fixes and reliability work across `admin` / `sdk` / `bootstrap` (instance heartbeats and cluster master election, Oracle compatibility, Netty event-loop lifecycle, SDK response handling), plus registry cleanup, dependency slimming and release notes. Currently working on MQTT clientId takeover and QoS2 dedup, plugin fault-tolerance eviction and K8s scaler wiring.

<details>
<summary>  34 PRs · ✅ 25 merged · 🟡 8 open · ⛔ 1 closed &nbsp;(click to expand)</summary>
<br>

| PR | Status | Title |
| --- | --- | --- |
| [#7939](https://github.com/apache/shenyu/pull/7939) | 🟡 Open | fix(mqtt): take over duplicate clientIds and fence stale-connection cleanup (#7918) |
| [#7938](https://github.com/apache/shenyu/pull/7938) | 🟡 Open | fix(mqtt): deduplicate retransmitted qos2 publishes with inbound in-flight state (#7919) |
| [#7925](https://github.com/apache/shenyu/pull/7925) | 🟡 Open | fix(plugin): evict cached fault-tolerance handles when explicitly cleared (#7914) |
| [#7917](https://github.com/apache/shenyu/pull/7917) | 🟡 Open | fix(admin): back k8s client/scaler beans off their own types and guard the missing client (#7912) |
| [#7887](https://github.com/apache/shenyu/pull/7887) | ✅ Merged | refactor(admin): drop commons-io by replacing two IOUtils.copy call sites (#7607) |
| [#7858](https://github.com/apache/shenyu/pull/7858) | ✅ Merged | fix(base): resolve partial identities when removing metadata (#7790) |
| [#7850](https://github.com/apache/shenyu/pull/7850) | ✅ Merged | perf(ai): parse the rule words only on a dictionary cache miss (#7829) |
| [#7846](https://github.com/apache/shenyu/pull/7846) | ✅ Merged | test(admin): use json payloads in the heartbeat metadata tests (#7692) |
| [#7844](https://github.com/apache/shenyu/pull/7844) | ⛔ Closed | fix(ai): build the sensitive-word dictionary off the redis io threads (#7830) |
| [#7798](https://github.com/apache/shenyu/pull/7798) | ✅ Merged | fix(rewrite): look up rewrite metadata with an empty prefix when context-path is absent (#7796) |
| [#7797](https://github.com/apache/shenyu/pull/7797) | ✅ Merged | fix(admin): forward instance heartbeats to the master admin (#7778) |
| [#7786](https://github.com/apache/shenyu/pull/7786) | ✅ Merged | fix(sdk): give each invocation independently owned header values (#7771) |
| [#7782](https://github.com/apache/shenyu/pull/7782) | ✅ Merged | fix(admin): stop the master selector scheduler on cluster shutdown (#7774) |
| [#7780](https://github.com/apache/shenyu/pull/7780) | 🟡 Open | fix(admin): keep accepted heartbeats when restoring instances from the database (#7763) |
| [#7776](https://github.com/apache/shenyu/pull/7776) | 🟡 Open | fix(admin): ignore heartbeats with an incomplete instance identity (#7764) |
| [#7766](https://github.com/apache/shenyu/pull/7766) | 🟡 Open | fix(logging): clear the selector sampler override when its handle is emptied (#7750) |
| [#7758](https://github.com/apache/shenyu/pull/7758) | ✅ Merged | fix(admin): order Oracle operation logs before applying the row limit (#7739) |
| [#7756](https://github.com/apache/shenyu/pull/7756) | ✅ Merged | fix(admin): use two-argument CONCAT for Oracle operation-log searches (#7738) |
| [#7754](https://github.com/apache/shenyu/pull/7754) | ✅ Merged | fix(admin): use ROWNUM for the Oracle instance identity lookup (#7724) |
| [#7746](https://github.com/apache/shenyu/pull/7746) | 🟡 Open | fix(dubbo): resolve single name-mapped parameters instead of using the mapping JSON as a type name (#7736) |
| [#7742](https://github.com/apache/shenyu/pull/7742) | ✅ Merged | fix(admin): expose the instance record id in the instance API (#7731) |
| [#7740](https://github.com/apache/shenyu/pull/7740) | ✅ Merged | fix(sdk): accept all 2xx responses and validate failures on void methods (#7711) |
| [#7729](https://github.com/apache/shenyu/pull/7729) | ✅ Merged | fix(sdk): quote path-variable replacement values in the Spring SDK (#7712) |
| [#7726](https://github.com/apache/shenyu/pull/7726) | ✅ Merged | fix(bootstrap): own and dispose the gateway's custom Netty event loops (#7715) |
| [#7722](https://github.com/apache/shenyu/pull/7722) | ✅ Merged | fix(register): report the bootstrap instance type from the independent heartbeat (#7696) |
| [#7721](https://github.com/apache/shenyu/pull/7721) | ✅ Merged | fix(admin): refresh instance metadata on repeated heartbeats (#7692) |
| [#7710](https://github.com/apache/shenyu/pull/7710) | ✅ Merged | fix(admin): initialise V1Scale spec before setting replicas (#7698) |
| [#7699](https://github.com/apache/shenyu/pull/7699) | ✅ Merged | fix(logging): shutdown hook cleanup reaches close0 when hook removal throws (#7686) |
| [#7691](https://github.com/apache/shenyu/pull/7691) | ✅ Merged | fix(admin): exclusion search drops plugins matching any searchable field (#7690) |
| [#7677](https://github.com/apache/shenyu/pull/7677) | ✅ Merged | refactor(admin): rename misspelled loged column/field to logged in selector and rule (#7589) |
| [#7663](https://github.com/apache/shenyu/pull/7663) | ✅ Merged | fix(log): reduce routine matching and configuration-sync log volume (#7643) |
| [#7642](https://github.com/apache/shenyu/pull/7642) | ✅ Merged | docs: record registry core/implementation decoupling in release notes (#7585) |
| [#7618](https://github.com/apache/shenyu/pull/7618) | ✅ Merged | build: remove misspelled log4j-1.2-api property and obsolete zookeeper log4j exclusion (#7609) |
| [#7611](https://github.com/apache/shenyu/pull/7611) | ✅ Merged | refactor(registry): remove the orphaned shenyu-registry-consul module (#7583) |

</details>

### [agentic-ai-java/argi](https://github.com/agentic-ai-java/argi)

> **ARGI** — Agent Runtime and Graph Intelligence (⭐ 127): a Java agent framework built on Spring AI, with a graph runtime, multi-agent workflows and visual administration.

**What I did**: The opt-in ToolCall argument-validation gate (local JSON Schema `$ref` expansion, resource limits), a unified tool-failure status contract, the AgentResult delivery contract with structured-output finalizer, and a fix for user-registered KeyStrategy loss during state cloning. Currently working on streaming delivery boundaries.

<details>
<summary>  8 PRs · ✅ 6 merged · 🟡 1 open · ⛔ 1 closed &nbsp;(click to expand)</summary>
<br>

| PR | Status | Title |
| --- | --- | --- |
| [#179](https://github.com/agentic-ai-java/argi/pull/179) | 🟡 Open | feat(agent): add streaming delivery boundary with bounded format repair (T39) |
| [#173](https://github.com/agentic-ai-java/argi/pull/173) | ✅ Merged | feat(agent): add AgentResult delivery contract with opt-in structured output finalizer (T39) |
| [#167](https://github.com/agentic-ai-java/argi/pull/167) | ✅ Merged | feat(agent): add registered business outcome mapping and outcome consistency fixes (T38) |
| [#159](https://github.com/agentic-ai-java/argi/pull/159) | ✅ Merged | feat(agent): unify tool failure status contract and remove null-status error paths (T38) |
| [#151](https://github.com/agentic-ai-java/argi/pull/151) | ✅ Merged | feat(agent): add resource limits and local $ref expansion to tool argument validation (T31) |
| [#149](https://github.com/agentic-ai-java/argi/pull/149) | ✅ Merged | feat(agent): add opt-in ToolCall argument validation gate before dispatch (T31) |
| [#116](https://github.com/agentic-ai-java/argi/pull/116) | ⛔ Closed | chore(graph): add missing Apache license header to CloneStateKeyStrategyPollutionTest |
| [#115](https://github.com/agentic-ai-java/argi/pull/115) | ✅ Merged | fix(graph): preserve user-registered input KeyStrategy across state cloning and snapshots |

</details>
