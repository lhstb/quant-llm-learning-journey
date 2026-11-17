# LLM 参数笔记：temperature / top_p / max_tokens

> 适用：DeepSeek `deepseek-chat`（OpenAI 兼容接口）。
> 原则：先固定 prompt 和模型，再调参数；每次只动一个；用 20-50 条样例做评测。
> 范围提示：temperature 常见 0-2，top_p 常见 0-1；具体默认值与上限以模型官方文档为准。

## 1. temperature（温度）

**含义**：控制采样时的随机性。温度越低，概率分布越“尖”，模型越倾向选高概率词，输出更稳定、保守；温度越高，分布越“平”，输出更多样、更有创意，也更容易跑偏。

**取值直觉**：

- `0`：尽量确定性，适合分类、抽取、代码、结构化输出。
- `0.1-0.3`：低随机性，适合大多数工程任务。
- `0.7-1.0`：平衡，适合写作、头脑风暴。
- `>1.0`：高多样性，容易发散；生产环境慎用。

**注意**：

- `temperature=0` 也不保证每次逐字相同，后端批处理、硬件和版本变化都可能带来差异。
- 不要用高温度来“让模型更聪明”；它主要改变随机性，不改变知识边界。
- 量化场景要的是可复现和标签一致性，优先低温度。

## 2. top_p（核采样）

**含义**：nucleus sampling（核采样）。模型只从“累积概率达到 top_p 的最小 token 集合”里采样。

- `top_p=1.0`：保留全部候选，不额外截断。
- `top_p=0.9`：保留最可能的 90% 概率质量，去掉长尾。
- `top_p` 越低，输出越聚焦、越保守；越高，候选越多、越多样。

**与 temperature 的关系**：

- 两者都影响随机性，通常**只重点调一个**，不要同时大幅调低。
- 想要稳定输出：优先 `temperature` 调低，`top_p` 保持 `0.9-1.0`。
- 想要减少长尾胡说：可以适度降低 `top_p`，但不要低到让表达变得僵硬。

## 3. max_tokens（最大生成长度）

**含义**：限制模型本次回复最多生成多少 token，**不包含 prompt 的 token**，也不是模型的上下文窗口。

- 太小：代码/JSON 被截断，回答不完整。
- 太大：不会自动让答案更好，但会增加延迟上限；实际计费通常按真实生成量，不按这个上限。
- 建议按任务预留：短标签 20-50；带理由的 JSON 120-300；单个代码函数 800-2000；完整文件 2000-4000。

**注意**：

- 结构化输出（JSON）要把“最坏情况”的长度算进去，避免最后一个括号被截断。
- 如果经常截断，先增加 `max_tokens`，再检查 prompt 是否要求模型输出过多内容。
- 推理型模型的 token 规则可能不同，以对应模型文档为准。

## 4. 两个场景的推荐取值

| 场景 | temperature | top_p | max_tokens | 说明 |
| --- | --- | --- | --- | --- |
| 写代码 | `0.0-0.3`，起步 `0.2` | `0.9-1.0`，起步 `1.0` | 单函数 `800-1500`；整文件 `2000-4000` | 低随机性，减少“自创 API”；仍必须跑测试 |
| 量化新闻情感分析 | `0.0-0.2`，起步 `0.1` | `0.8-0.95`，起步 `0.9` | 单条 `120-250`；批量按条数增加 | 标签一致性优先；JSON 输出要留足长度 |

### 写代码

- 推荐：`temperature=0.2`、`top_p=1.0`、`max_tokens=1500`。
- 如果模型爱加解释，在 prompt 里写“只输出代码，不要解释”，比继续降温度更有效。
- 如果生成的代码总是调用不存在的库，降低温度 + 在 prompt 里给出可用依赖清单。
- 参数不能替代测试：生成后至少跑语法检查、单测和一次真实输入。

### 量化新闻情感分析

- 推荐：`temperature=0.1`、`top_p=0.9`、`max_tokens=200`。
- 输出建议固定为 JSON：`label`（positive/negative/neutral）、`confidence`（0-1）、`reason`（一句话）。
- 同一批新闻要跑 2-3 次做一致性检查；如果标签漂移，优先降低 temperature，而不是反复改 prompt。
- 批量分析时，`max_tokens` 按“单条上限 × 条数”估算，并留 20% 余量。
- 如果使用 JSON 模式，prompt 中要明确出现“JSON”，并对返回结果做 schema 校验。

## 5. 两套起步配置

### 写代码

```python
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是资深 Python 工程师。只输出可运行代码，不要解释。"},
        {"role": "user", "content": "实现一个计算对数收益率的函数，并写 3 个 pytest 用例。"},
    ],
    temperature=0.2,
    top_p=1.0,
    max_tokens=1500,
)
```

### 量化新闻情感分析

```python
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": "你是金融新闻情感分析器，只输出 JSON。"},
        {"role": "user", "content": (
            "判断下面新闻对该公司股价的影响，输出 JSON："
            '{"label":"positive|negative|neutral","confidence":0.0,"reason":"一句话"}。'
            "新闻：公司发布公告，预计全年净利润同比增长 30%。"
        )},
    ],
    temperature=0.1,
    top_p=0.9,
    max_tokens=200,
    response_format={"type": "json_object"},
)
```

## 6. 调参顺序

1. **固定 prompt、模型和评测集**：准备 20-50 条代表性样本。
2. **先调 temperature**：从 `0.1` 开始，观察稳定性、正确率和多样性。
3. **再调 top_p**：只有在温度确定后，才用它微调长尾；通常保持 `0.9-1.0`。
4. **最后调 max_tokens**：确保不截断，再压缩成本。
5. **记录指标**：准确率/F1、JSON 解析成功率、平均延迟、token 成本、人工可读性。
6. **每次只改一个参数**，否则无法判断收益来自哪里。

## 7. 常见误区

- 同时把 `temperature` 和 `top_p` 调得很低：输出可能变得僵硬、重复，甚至更容易卡住。
- 用 `temperature` 解决格式问题：格式问题优先靠 prompt、JSON 模式和 schema 校验解决。
- `max_tokens` 设得太小：代码或 JSON 被截断，却误以为是模型能力问题。
- 只看一两次输出就定参数：至少跑 20 条样本，并做多次一致性检查。
- 把 API Key 写进代码或提交 `.env`：这是最严重的安全问题，密钥只放环境变量。

## 8. 与本计划的关系

- **W1**：先用 `w1_api_test.py` 跑通调用，理解请求参数与 token 用量。
- **W2-W4**：用低温度做结构化抽取和 Prompt 对比实验。
- **W5-W8**：把参数固定下来，接入 RAG 评测，避免“每次回答都不一样”。
- **量化文本因子**：情感/事件抽取必须保证标签一致性，低温度 + JSON 校验是默认配置。

## 9. 实测记录：temperature 0.1 vs 0.9（2026-11-17）

**实验设置**

- 模型：`deepseek-chat`
- Prompt：`用一句话解释一下最大回撤`
- 固定（按脚本默认值）：`top_p=0.9`、`max_tokens=200`
- 变量：`temperature=0.1` 与 `temperature=0.9`

> 说明：原始输出未在对话中粘贴，下表先保留结论与观察；把两段原文发我后可回填。

| temperature | 输出原文 | 观察 |
| --- | --- | --- |
| 0.1 | 待回填 | 表述更稳定、术语更严谨，适合专业解释 |
| 0.9 | 待回填 | 表述更发散，可能加入比喻或扩展，但精确性下降 |

**结论**

- 低温度适合严谨的专业任务：定义、代码、抽取、金融解释，优先 `0.0-0.3`。
- 高温度适合发散性的创意任务：起标题、头脑风暴、营销文案，可用 `0.7-1.0`。
- 这只是单次对比；正式结论至少重复 3 次，并用 20 条 prompt 做评测。
- 高温度不是“更聪明”，只是方差更大；事实性内容仍需人工校验。

**复现命令**

```powershell
python w1_api_test.py --prompt "用一句话解释一下最大回撤" --temp 0.1 --top_p 0.9 --max_tokens 200
python w1_api_test.py --prompt "用一句话解释一下最大回撤" --temp 0.9 --top_p 0.9 --max_tokens 200
```

## 参考

- DeepSeek Chat Completion API：https://api-docs.deepseek.com/api/create-chat-completion
- DeepSeek 参数设置建议：https://api-docs.deepseek.com/quick_start/parameter_settings
