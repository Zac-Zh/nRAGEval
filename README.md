# nRAGEval: Native Chinese RAG Evaluation Framework

**定位**：面向中文 RAG 场景的原生评测框架。

> **English TL;DR**: `nrageval` (Native RAG Eval) is a Chinese-native RAG evaluation framework. Unlike RAGAS / DeepEval / RAGChecker which optimize for answer correctness, `nrageval` optimizes for **source legitimacy** — if your RAG pipeline answers correctly but by leaking model memory instead of using the knowledge base, `nrageval` will catch it. Ships with five evaluation dimensions (KBC / RA / CT / NCP / AC) and two automated test generators (Counterfactual Compliance Test + Bidirectional Consistency Test).

---

## 1. 现有框架的不足

一个来自阶段一实测的案例：知识库只包含 `1993年发布了DICOM标准3.0`。用户问 `DICOM标准的最新版本是多少？`，RAG 回答 `DICOM最新版本是3.0，该版本于1993年发布`。

| 框架 | Faithfulness 评分 | 判断 |
|---|---|---|
| **RAGAS** | 0.50 | 部分支持 ⚠️ |
| **DeepEval** | 1.00 | 完全支持 ✓ |
| **RAGChecker** | 88.8 | 高忠实度 ✓ |
| **人工判断** | 0.00 | 越界推断 ✗ |
| **nrageval KBC** | 0.50 | 半数 claim 越界 ✗（阶段一回测实测） |

问题：所有现有框架的 faithfulness 指标都只检查 claim 和 context 的字面重叠，不检查时间敏感限定词如最新是否越界。回答中的 `3.0` 和 `1993年` 都字面出现在原文里，于是它们给高分。用户看到这个回答，会以为自己从知识库得到了确凿的事实，但其实模型使用了自己的过时知识。

---

## 2. 五个评测维度

| 维度 | 缩写 | 度量 | 主要捕获的失败 |
|---|---|---|---|
| Knowledge Boundary Compliance | **KBC** | 每条声明能否在知识库中找到来源？时间敏感词/泛化/推断算越界 | 模型用自身知识冒答 |
| Refusal Appropriateness | **RA** | 知识库没答案时，系统是否正确拒答？ | 过度回答 / 过度拒答 |
| Citation Traceability | **CT** | 回答能否定位到具体条款/章节？ | 答案对但无法溯源 |
| Numerical & Clause Precision | **NCP** | 数值/日期/编号是否与原文完全一致（语义等价计通过）？ | 金额/期限/版本号偏差 |
| Answer Completeness | **AC** | 问题的所有要点是否都被覆盖？ | 跨段落问题遗漏要点 |

不提供加权总分。不同场景下权重完全不同（政策法规重 NCP，FAQ 重 AC），加权会误导用户。nrageval 提供 5 维雷达图 + 场景预设（policy/technical/faq）定义关键指标。

### 场景预设与及格线

nrageval 内置三个场景预设，每个场景定义了各指标的**及格线**和**角色**（关键/参考）。关键指标未达标 → 红灯；关键达标但某指标劣于 baseline → 黄灯；全部达标且优于 baseline → 绿灯。

| 场景 | KBC | RA | NCP | CT | AC |
|---|---|---|---|---|---|
| **policy**（政策法规）| ≥0.95 关键 | =1.0 关键 | =1.0 关键 | ≥0.7 参考 | ≥0.8 参考 |
| **technical**（技术手册）| ≥0.90 关键 | =1.0 关键 | ≥0.95 关键 | ≥0.5 参考 | ≥0.85 关键 |
| **faq**（FAQ/客服）| ≥0.85 关键 | ≥0.8 参考 | ≥0.9 参考 | ≥0.3 参考 | ≥0.9 关键 |

设计理由：
- policy 场景 KBC/RA/NCP 零容错：政策解读的任何越界都可能导致法律误读。
- technical 场景 AC 是关键：API/参数/命令的遗漏会导致操作失败，但适度的通用说明可接受。
- faq 场景 RA 降为 reference：客服场景下“建议联系人工”也是合理回答；AC 是关键，因为“问三答一”体验极差。

场景预设在 `nrageval/presets.py` 中定义，带完整注释说明每个阈值的推导依据，待用户反馈迭代。

---

## 3. 两种自动化测试方法

### 3.1 Counterfactual Compliance Test（反事实合规测试）

**原理**：从用户知识库中抽取事实（`有效期5年`），替换为反事实（`有效期3年`），构建反事实知识库，跑 RAG pipeline，检查模型输出与哪个版本一致。

- 模型答 `3年` → pass（忠于知识库）
- 模型答 `5年` → **fail_memory_leak**（用了模型记忆，这是现有框架无法检测的致命问题）
- 模型拒答 → pass（拒答优于越界）

优势：零争议。不需要 LLM judge 做语义推理，字符串匹配即可。零成本，只需跑一次 RAG pipeline。

### 3.2 Bidirectional Consistency Test（双向一致性测试）

原理：知识库中的事实关系是双向的。正向查询 `A→B` 和反向查询 `B→A` 应该给出一致的结果。不一致揭示了 embedding 检索/生成阶段的方向性偏差。

```
正向: 医疗器械注册证有效期是多少年？     → 应答 5年
反向: 哪些证件有效期是5年？              → 应枚举包含注册证的所有证件
```

---

## 4. Quick Start

```bash
# 安装
pip install -e .

# 设置 API keys
export DEEPSEEK_API_KEY=sk-...
export DASHSCOPE_API_KEY=sk-...  # 可选，用于 qwen judge
```

Python API：

```python
from nrageval import EvalSample, evaluate, evaluate_against_preset, compare_with_baseline

samples = [
    EvalSample(
        question="医疗器械注册证的有效期是多少年？",
        answer="医疗器械注册证有效期为5年。",
        contexts=["第二十二条 医疗器械注册证有效期为5年..."],
        ground_truth="5年",
        metadata={"qid": "q1", "category": "in_scope"},
    ),
]

# 单 judge
results = evaluate(samples, judge="deepseek-chat")
print(results[0].scores)
# {'kbc': 1.0, 'ra': 1.0, 'ct': 0.7, 'ncp': 1.0, 'ac': 1.0}

# 场景达标判断
avg_scores = {"kbc": 0.96, "ra": 1.0, "ct": 0.75, "ncp": 1.0, "ac": 0.85}
verdict = evaluate_against_preset(avg_scores, scene="policy")
print(verdict["signal"])  # 'green' / 'yellow' / 'red'
print(verdict["critical_failures"])  # []

# 与 naive baseline 对比
import json
with open("data/baseline/naive_rag_baseline.json") as f:
    baseline = json.load(f)
cmp = compare_with_baseline(avg_scores, baseline)
print(cmp["summary"])  # "您的系统在 KBC/CT 上优于 naive baseline..."

# 双 judge（自动标记 low_confidence）
results = evaluate(samples, judge=["deepseek-chat", "qwen-plus"])
print(results[0].confidence)  # 'high' 或 'low'
```

---

## 5. CLI 用法

```bash
# 1) 基础评测 → HTML 报告（不做及格线判断）
nrageval evaluate \
    --data results/rag_outputs/deepseek_chat_outputs.json \
    --metrics kbc,ra,ct,ncp,ac \
    --judge deepseek-chat \
    --output report/eval_report.html

# 2) 场景评测 + baseline 对比（推荐）
nrageval evaluate \
    --data results/rag_outputs/deepseek_chat_outputs.json \
    --judge deepseek-chat \
    --scene policy \
    --baseline data/baseline/naive_rag_baseline.json \
    --output report/eval_report.html
# 报告顶部会显示 🟢/🟡/🔴 信号灯、关键指标达标详情、vs baseline diff

# 3) 双 judge 评测（标记 low_confidence 评分）
nrageval evaluate \
    --data results/rag_outputs/deepseek_chat_outputs.json \
    --judge deepseek-chat,qwen-plus \
    --output report/eval_report.html

# 3) 生成反事实测试集（一键从用户知识库）
nrageval counterfactual \
    --knowledge-base data/raw/ \
    --judge deepseek-chat \
    --num-samples 20 \
    --output data/counterfactual_tests.jsonl

# 4) 生成双向一致性测试集
nrageval bidirectional \
    --knowledge-base data/raw/ \
    --judge deepseek-chat \
    --num-samples 20 \
    --output data/bidirectional_tests.jsonl

# 5) 跑反事实测试（无需 LLM judge，纯规则匹配）
nrageval test-counterfactual \
    --tests data/counterfactual_tests.jsonl \
    --pipeline-output results/counterfactual_rag_outputs.json \
    --output report/counterfactual_report.html
```

---

## 6. 回测结果（阶段一数据验证）

nrageval 在阶段一 Failure Report 识别出的 6 个典型失败模式上，**6/6 全部正确捕获**。结果见 [`tests/backtest_results.json`](tests/backtest_results.json)。

| 失败模式 | 期望行为 | nrageval 实测 | 结果 |
|---|---|---|---|
| DOC-2 Q09 DICOM 越界推断（“最新版本”外加） | KBC ≤ 0.5 | KBC=0.5（1/2 claim 被判 violation）| ✓ |
| DOC-2 Q10 pydicom 冒答 | RA=0.0 | RA=0.0（信息不充分但未拒答）| ✓ |
| DOC-1 Q09 收费标准正确拒答 | RA=1.0 | RA=1.0（检测到“没有提及”）| ✓ |
| DOC-1 Q05 罚款金额精度 | NCP 非 None | NCP=1.0（提取到硬事实）| ✓ |
| DOC-3 Q08 变更情形列举不全 | AC < 1.0 | AC < 1.0（漏列供应商变更/参考品更新）| ✓ |
| DOC-1 Q07 claim extractor 反碎片化 | claim count < 13 | **11** claims（vs RAGAS 的 16+）| ✓ |

在 DOC-2 Q09（越界推断）这个现有三大框架全部失效的场景上，nrageval 的 KBC 指标成功区分了字面 supported 和越界推断 claim。

---

## 7. Naive RAG Baseline

nrageval 内置了一组 **naive RAG baseline** 数据：LlamaIndex + ChromaDB + DashScope embedding (`text-embedding-v3`) + DeepSeek-Chat、`chunk_size=512`、`top-k=5`、**无 reranking、无 query rewriting**，在 30 条中文医疗器械问题上的五维评分。

用户跑完自己的系统后，可以通过 `--baseline data/baseline/naive_rag_baseline.json` 量化优化收益。

**Overall baseline**（DeepSeek-Chat as judge, 30 samples）：

| 指标 | 分数 | 解读 |
|---|---|---|
| **KBC** | 0.789 | ~21% 的 claim 越界（典型越界：from “1993年发布3.0” 外推为 “最新版本是3.0”）|
| **RA** | 0.733 | 较弱的拒答能力（out_of_scope 类 6 条中 3 条冒答）|
| **CT** | 0.643 | 引用追溯性最弱（naive pipeline 无 “引用来源” 指令）|
| **NCP** | 1.000 | 数值准确度完美（无数值错误，但不覆盖“推断越界”类问题）|
| **AC** | 0.889 | 单点问题回答完整，跨段落问题会遗漏 |

> Naive RAG 在 NCP 上做得好，但在 KBC/RA/CT 上有明显问题。

详细 baseline 按 doc_id × category 聚合的数据见 [`data/baseline/naive_rag_baseline.json`](data/baseline/naive_rag_baseline.json)。

---

## 8. 与现有框架的对比

| 能力 | RAGAS | DeepEval | RAGChecker | **nrageval** |
|---|---|---|---|---|
| 中文原生 rubric 校准 | ✗（英文化严重）| ⚠️（Qwen 生成倾向英文）| ✗ | **✓** |
| 时间敏感词越界检测 | ✗ | ✗ | ⚠️（self_knowledge，但未入分）| **✓** |
| 显式拒答合理性评分 | ✗ | ⚠️ | ✗ | **✓** |
| Citation Traceability | ✗ | ✗ | ✗ | **✓** |
| 反事实合规测试生成 | ✗ | ⚠️（通用合成数据）| ✗ | **✓** |
| 双向一致性测试 | ✗ | ✗ | ✗ | **✓** |
| 反碎片化 claim extractor | ✗（16+ 碎片）| ⚠️ | ✗（spacy 分句） | **✓**（LLM + 阶段一 few-shot 校准）|
| Judge 间一致性标记 | ✗ | ✗ | ✗ | **✓**（low_confidence）|



---

## 9. 目录结构

```
nrageval/
├── nrageval/
│   ├── metrics/         # KBC / RA / CT / NCP / AC 5 个指标
│   ├── generators/      # Counterfactual + Bidirectional 生成器
│   ├── judge/           # DeepSeek / Qwen / Rule-based judge
│   ├── claim/           # 反碎片化 claim extractor
│   ├── report/          # HTML 报告 + 雷达图
│   ├── evaluator.py     # evaluate() 主入口
│   ├── cli.py           # nrageval CLI
│   └── schemas.py       # 数据结构
├── prompts/             # 8 个 rubric prompt（基于阶段一数据 few-shot 校准）
├── tests/               # 单元测试 + 阶段一回测
└── README.md
```

---

## 10. License

MIT

---

## 11. Citation

如果本项目对你有帮助，请引用：

```
nrageval: A Chinese-native RAG evaluation framework with source legitimacy priority.
2026. https://github.com/.../nrageval
```

---

## 附: 阶段一实验数据说明

nrageval 的所有 rubric prompt 和指标阈值都基于一个系统性实验校准：用 3 份中文医疗器械领域文档（政策法规 / 技术手册 / FAQ）、30 条人工标注问题、RAGAS + DeepEval + RAGChecker 三大现有框架 × DeepSeek + Qwen 双 judge 做对照。阶段一 Failure Report（`/root/autodl-tmp/Project/report/failure_report.md`）系统记录了现有框架在中文场景下的所有可观察问题，其中 6 个典型失败案例已进入 nrageval 的回测集（步骤 9）。
