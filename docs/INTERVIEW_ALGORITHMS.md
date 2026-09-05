# Agent Backend / AI Application 面试算法与 Coding 手册

> 版本：2026-09-06，第一版。
>
> 目标岗位：Agent Backend、AI Application Engineer、大模型应用研发、LLM Application Engineer、AI 全栈，以及偏后端的智能体研发。
>
> 结论先写在前面：**LeetCode Hot 100 很适合做算法主干，但不够覆盖完整面试。** 对这类岗位，真正需要的是：
>
> **Hot 100 + 高频补充算法 + SQL + Backend Coding + CS 基础 + System Design + RAG/Agent 项目深挖 + AI Coding。**

## 1. 为什么 Hot 100 不能当全部

Hot 100 的价值很高，因为它覆盖数组、哈希、链表、树、图、回溯、二分、堆、贪心、动态规划等高频模式。把这些模式练熟，比盲目刷几百道随机题有效。

但 2026 年的后端/Agent 面试已经明显不只考传统 LeetCode：

- 腾讯后端样本同时出现线程池、B/B+ 树、HTTP/HTTPS、WebSocket/SSE、MCP、Redis 分布式锁和“手写滑动窗口限流”。
  - <https://www.nowcoder.com/discuss/924491135685234688>
- 字节“中国交易与广告 Agent 后端开发工程师”样本直接考 Agent 基础设施、Redis 热点 Key/大 Key，以及课程表进阶的拓扑排序。
  - <https://www.nowcoder.com/discuss/922660519729696768>
- 字节后端面经中同时出现 MQ、Redis、一致性、MCP/Skill、Agent、股票 DP、本地缓存设计等。
  - <https://www.nowcoder.com/discuss/922663186854092800>
- 腾讯样本要求解释 Agent、chunk 指标，并现场手写排序；另有 Linux 文本处理问题。
  - <https://www.nowcoder.com/discuss/924491686481231872>
- AI 应用实习面经已经会在 Agent/RAG 项目追问后继续问 Redis、IO 多路复用和数据库优化。
  - <https://api-cdn.nowcoder.com/feed/main/detail/40920533fad14136bff01c3928c7e953>

因此训练目标不能只是“我记住了 100 道答案”，而应该是：

1. 看见题能识别模式。
2. 能从空白编辑器写出来。
3. 能解释时间/空间复杂度。
4. 能处理边界情况。
5. 能把同一种数据结构迁移到后端工程题。
6. 能在 30–60 分钟完成一个小型 AI Backend Coding Task。

---

# Part A：LeetCode / 数据结构算法主干

## 2. 推荐学习顺序

不要按 LeetCode 页面随机顺序刷。按“模式依赖关系”学习：

1. 数组 + Hash
2. 双指针
3. 滑动窗口
4. 前缀和
5. 链表
6. 栈 / 队列
7. 二叉树 / BST
8. 堆 / TopK
9. 二分
10. 图：DFS / BFS
11. 拓扑排序 / Union Find
12. 回溯
13. 贪心
14. 动态规划
15. 区间 / 单调栈 / 单调队列
16. 高频工程数据结构：LRU、Trie

每类题都按下面过程：

**识别信号 → 最小模板 → 2 道简单题 → 3–5 道典型题 → 变化题 → 限时复写。**

第一次学习可以看解析；第二次必须自己写；第三次隔几天在空白环境复写。

## 3. 数组与 Hash

### 3.1 你需要识别什么

出现下面词时，先想到 Hash：

- “是否出现过”
- “次数”
- “两数关系”
- “去重”
- “分组”
- “O(1) 查找”

必须掌握：

- Two Sum
- Group Anagrams
- Longest Consecutive Sequence
- Top K Frequent Elements（顺带堆）

面试要求：不能只说 dict 很快，要知道 Python dict/set 平均查找 O(1)，也要知道这是平均复杂度，不是任意情况下绝对 O(1)。

### 3.2 最小 Python 模板

```python
def two_sum(nums, target):
    seen = {}
    for i, x in enumerate(nums):
        need = target - x
        if need in seen:
            return [seen[need], i]
        seen[x] = i
    return []
```

要能解释：为什么先查再写可以避免同一元素被使用两次。

---

## 4. 双指针

识别信号：

- 有序数组
- 两端向中间
- 原地修改
- 快慢指针
- 判断环

必须掌握：

- Move Zeroes
- Container With Most Water
- 3Sum
- Linked List Cycle（快慢指针迁移）

关键思想不是“背 left/right”，而是回答：**移动哪个指针可以排除一批不可能答案？**

---

## 5. 滑动窗口

这对后端面试尤其重要，因为它会直接迁移到“滑动窗口限流”。

识别信号：

- 连续子数组 / 子串
- 最长 / 最短
- 满足某个窗口条件
- 最近 N 秒请求

必须掌握：

- Longest Substring Without Repeating Characters
- Find All Anagrams in a String
- Minimum Window Substring
- Sliding Window Maximum（结合单调队列）

通用框架：

```python
left = 0
for right, x in enumerate(data):
    add(x)
    while window_invalid():
        remove(data[left])
        left += 1
    update_answer(left, right)
```

真正要学的是：

- 什么时候收缩？
- `while` 还是 `if`？
- 什么时候更新答案？
- 窗口状态如何 O(1) 更新？

工程迁移：后面会用同样思想实现 request rate limiter。

---

## 6. 前缀和与差分

Hot100 对这部分的体感可能不如 DP 强，但笔试很实用。

必须理解：

```text
prefix[i] = nums[0] + ... + nums[i-1]
区间 [l, r] = prefix[r+1] - prefix[l]
```

典型题：

- Subarray Sum Equals K
- Range Sum Query
- 二维前缀和
- Difference Array（区间批量加减）

为什么重要：很多“连续区间统计”不能用滑动窗口，因为数组可能存在负数。

---

## 7. 链表

必须掌握：

- Reverse Linked List
- Merge Two Sorted Lists
- Linked List Cycle
- Intersection of Two Linked Lists
- Remove Nth Node From End
- Swap Nodes / Reverse K Group（进阶）

强制养成 dummy node 习惯，尤其是删除头结点场景。

面试时至少能解释：

- 为什么链表随机访问 O(n)
- 为什么插入删除“已知节点位置”可以 O(1)
- 链表和动态数组的内存局部性差异

---

## 8. 栈、队列、单调结构

必须掌握：

- Valid Parentheses
- Min Stack
- Daily Temperatures
- Largest Rectangle in Histogram
- Sliding Window Maximum

单调栈识别信号：

> “对每个元素，找左/右边第一个更大或更小元素”。

单调队列识别信号：

> “固定窗口内不断求最大/最小”。

---

## 9. 二叉树 / BST

这是最不能掉的面试基础之一。

必须掌握：

- Preorder / Inorder / Postorder
- Level Order Traversal
- Maximum Depth
- Invert Binary Tree
- Diameter of Binary Tree
- Lowest Common Ancestor
- Validate BST
- Kth Smallest in BST
- Serialize / Deserialize Binary Tree（进阶）

递归题每次都问自己三件事：

1. 当前函数定义是什么？
2. 子问题返回什么？
3. 当前节点怎样组合子问题？

例如最大深度：

```python
def depth(node):
    if node is None:
        return 0
    return 1 + max(depth(node.left), depth(node.right))
```

不要把递归理解成“神奇地自己调用自己”，而是把函数当成已经能解决子树问题的黑盒。

---

## 10. 堆 / TopK

Agent/后端系统经常涉及优先级、TopK、任务调度，因此堆很实用。

必须掌握：

- Kth Largest Element
- Top K Frequent Elements
- Merge K Sorted Lists
- Find Median from Data Stream（双堆）

Python `heapq` 默认最小堆。

要能解释：

- push/pop 为什么 O(log n)
- 取堆顶为什么 O(1)
- TopK 为什么常用大小为 K 的小顶堆

---

## 11. 二分查找

不只是“找一个数字”。

必须掌握三种：

1. 精确值
2. lower bound / upper bound
3. 对答案二分

典型题：

- Binary Search
- Search in Rotated Sorted Array
- Find First and Last Position
- Koko Eating Bananas / capacity 类答案二分

最常见错误是边界定义混乱。固定一种模板，不要一会 `[l, r]` 一会 `[l, r)`。

---

## 12. 图：DFS / BFS

必须掌握：

- Number of Islands
- Rotting Oranges
- Clone Graph
- Word Ladder（进阶 BFS）

DFS 更适合遍历/连通块；BFS 天然适合无权图最短步数。

要能从二维网格迁移到一般邻接表，而不是只会上下左右。

---

## 13. 拓扑排序与 Union Find

这是 Hot100 之外尤其值得补强的部分。

### 拓扑排序

字节 2026 Agent 后端样本已经出现“课程表进阶，输出可行学习路径”。

Kahn 模板：

```python
from collections import deque

def topo(n, edges):
    graph = [[] for _ in range(n)]
    indegree = [0] * n
    for a, b in edges:
        graph[a].append(b)
        indegree[b] += 1

    q = deque(i for i in range(n) if indegree[i] == 0)
    order = []
    while q:
        x = q.popleft()
        order.append(x)
        for y in graph[x]:
            indegree[y] -= 1
            if indegree[y] == 0:
                q.append(y)
    return order if len(order) == n else []
```

工程迁移：任务依赖 DAG、workflow dependency。

### Union Find

必须会：

- parent
- path compression
- union by rank/size

典型用途：动态连通性、合并账户、网络组件。

---

## 14. 回溯

识别信号：

- “所有组合/排列/方案”
- 选择一个 → 递归 → 撤销

必须掌握：

- Subsets
- Permutations
- Combination Sum
- Generate Parentheses
- Word Search

核心模板：

```python
def backtrack(path, choices):
    if done(path):
        ans.append(path.copy())
        return
    for choice in choices:
        if invalid(choice):
            continue
        path.append(choice)
        backtrack(path, next_choices(choice))
        path.pop()
```

---

## 15. 贪心

必须掌握：

- Jump Game
- Best Time to Buy and Sell Stock
- Partition Labels
- Merge Intervals（也属于区间）

学习重点：能够证明“局部最优为什么不会破坏全局最优”，而不是只背 if。

---

## 16. 动态规划

DP 不需要一开始刷最难题，但必须形成框架。

四步：

1. `dp[i]` 表示什么？
2. 状态转移从哪里来？
3. 初始化是什么？
4. 遍历顺序为什么这样？

必须掌握：

- Climbing Stairs
- House Robber
- Coin Change
- Longest Increasing Subsequence
- Longest Common Subsequence
- Edit Distance
- 0/1 Knapsack 思想
- Stock 系列状态机

不要只背一维数组公式；必须能先写二维/直观状态，再做空间优化。

---

## 17. 排序必须能手写

腾讯 2026 后端样本仍会直接问排序实现。

至少会：

- Quick Sort
- Merge Sort
- Heap Sort 原理

要能比较：

| 算法 | 平均 | 最坏 | 额外空间 | 稳定 |
|---|---:|---:|---:|---|
| Quick Sort | O(n log n) | O(n²) | 递归栈 | 否 |
| Merge Sort | O(n log n) | O(n log n) | O(n) | 是 |
| Heap Sort | O(n log n) | O(n log n) | O(1) 级原地 | 否 |

至少从空白编辑器写出 Quick Sort 或 Merge Sort。

---

## 18. Trie、LRU、LFU

### Trie

适用于前缀、词典、路由匹配等。

必须理解节点结构、insert、search、startsWith。

### LRU

这是**算法 + 后端工程交叉的必会题**。

目标复杂度：

- `get`: O(1)
- `put`: O(1)

经典结构：

**HashMap + Doubly Linked List**。

不要只会 Python `OrderedDict` 一行解决；面试至少能手写核心结构并解释为什么需要双向链表。

### LFU

不是所有岗位必须，但作为 LRU 进阶，理解“频率 + 最近使用”的组合管理。

---

# Part B：SQL 面试

## 19. 必须掌握的 SQL 能力

按顺序学习：

1. SELECT / WHERE / ORDER BY / LIMIT
2. INNER / LEFT JOIN
3. GROUP BY / HAVING
4. 子查询 / CTE
5. CASE WHEN
6. Window Function
7. Top N per group
8. 去重 / 重复记录
9. 连续日期/连续登录
10. 索引与 EXPLAIN
11. 事务 / 隔离级别
12. 慢查询优化

### 高频窗口函数

```sql
SELECT
    user_id,
    amount,
    ROW_NUMBER() OVER (
        PARTITION BY user_id
        ORDER BY amount DESC
    ) AS rn
FROM orders;
```

必须分清：

- `ROW_NUMBER`
- `RANK`
- `DENSE_RANK`

Backend 岗不能只会写 SELECT，还要解释索引、B+ Tree、最左匹配、回表、事务和慢 SQL。

---

# Part C：Backend Coding 手撕

## 20. 为什么要单独训练

这部分往往不是 LeetCode 标准题，但对 Agent Backend 很重要。

你应该能在面试中实现或至少清楚设计：

1. LRU Cache
2. thread-safe queue
3. producer-consumer
4. sliding-window rate limiter
5. token bucket
6. retry with exponential backoff
7. timeout wrapper
8. TTL cache
9. simple task scheduler
10. simple message queue
11. SSE stream endpoint
12. concurrency semaphore
13. connection pool 思路
14. distributed lock 思路
15. idempotent request handler

## 21. 滑动窗口限流

它把 LeetCode 滑动窗口直接变成工程题。

最小思路：每个用户保存最近窗口内时间戳；新请求到来时先删除窗口外旧时间，再判断数量。

```python
from collections import deque
from time import monotonic

class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window = window_seconds
        self.events = deque()

    def allow(self) -> bool:
        now = monotonic()
        cutoff = now - self.window
        while self.events and self.events[0] <= cutoff:
            self.events.popleft()
        if len(self.events) >= self.limit:
            return False
        self.events.append(now)
        return True
```

然后继续追问：

- 多线程安全吗？
- 多进程怎么办？
- 多机器怎么办？
- 为什么生产环境可能放 Redis？
- 时间漂移怎么办？
- 固定窗口、滑动日志、滑动计数、token bucket 各有什么取舍？

这才是完整面试训练。

## 22. Retry / Backoff

必须理解：

- 哪些错误可重试？
- 401 为什么通常不应盲目重试？
- 429 / 5xx 怎么处理？
- exponential backoff
- jitter
- 最大尝试次数
- 幂等性

Agent Tool 调用如果没有这些能力，很容易从“Demo”变成不可靠系统。

---

# Part D：AI Coding

## 23. 这是 Hot 100 完全覆盖不到的能力

目标：能够在 30–60 分钟内做出一个小型、可运行、边界清晰的 AI Backend 功能。

### 必练任务 1：FastAPI LLM Endpoint

要求：

- Pydantic request/response
- 参数校验
- timeout
- API error mapping
- 不泄露 key

### 必练任务 2：SSE Streaming

要求：

- 正确 content type
- 客户端断开
- error event
- cancellation
- 不把 SSE 与 WebSocket 混淆

### 必练任务 3：最小 Tool Calling Loop

输入：用户问题。

模型可以选择：

- calculator
- search_knowledge_base

你要完成：

1. tool schema
2. 参数校验
3. tool dispatch
4. timeout
5. tool error
6. 把结果返回模型
7. bounded loop，防止无限调用

### 必练任务 4：Simple RAG

要求：

- chunk
- retrieve
- top-k
- context
- prompt
- citation
- no-evidence refusal

面试重点不是重新实现 Qdrant，而是你是否理解整个数据流。

### 必练任务 5：Conversation State

要求：

- `thread_id`
- 消息状态
- 并发请求冲突怎么处理
- session 与 long-term memory 的区别

### 必练任务 6：Tool Reliability

给工具故意制造：

- timeout
- invalid JSON
- 429
- 500
- empty result

要求系统能分类，而不是统一返回“模型失败”。

### 必练任务 7：Agent Eval

给 20–30 个固定任务，至少记录：

- task success
- tool success
- wrong tool
- invalid argument
- timeout
- answer groundedness
- latency

---

# Part E：CS / Backend 八股与 System Design

## 24. 数据库

必须会解释：

- B+ Tree
- clustered / secondary index
- covering index
- back-to-table
- leftmost prefix
- transaction ACID
- isolation levels
- MVCC
- redo / undo / WAL 思想
- slow SQL
- pagination optimization

## 25. Redis

必须会：

- 常见数据结构
- 为什么快
- expiration
- eviction
- cache penetration / breakdown / avalanche
- hot key / big key
- persistence
- distributed lock
- Redis/MySQL consistency

## 26. Network

必须会：

- TCP vs UDP
- TCP reliability
- three-way handshake / four-way close
- HTTP / HTTPS
- HTTP status
- keep-alive
- SSE vs WebSocket
- reverse proxy / gateway
- 502 vs 504

## 27. OS / Concurrency

必须会：

- process vs thread
- context switch
- lock / deadlock
- thread pool
- IO multiplexing
- Python GIL
- async vs thread vs process
- producer-consumer

## 28. MQ / Distributed Basics

至少理解：

- 为什么用 MQ
- producer retry
- consumer retry
- duplicate message
- idempotency
- ordering
- message loss
- delayed/retry queue
- eventual consistency

## 29. Agent Backend System Design

最终要能设计：

> “一个支持长任务、工具调用、RAG、流式输出和失败恢复的企业 Agent 服务。”

建议按层讲：

1. API/Gateway：auth、rate limit、request id
2. Session/State：conversation、checkpoint
3. Orchestrator：planner / workflow / tool loop
4. Tool layer：registry、schema、permission、timeout
5. RAG：retrieval、rerank、context
6. Model layer：routing、fallback
7. Async jobs：queue、worker、durable state
8. Storage：Postgres / Redis / vector store
9. Safety：sandbox、permission、HITL
10. Observability：trace、logs、metrics、cost
11. Eval：offline regression + production feedback

不要求一上来微服务化。面试更看重你能不能解释容量、失败模式和 trade-off。

---

# Part F：题目清单怎么用

## 30. 第一阶段：Hot 100 主干

目标不是 100/100 打卡，而是这些模式做到“隔几天仍能从空白写出”。

建议优先级：

### P0 必会模式

- Hash / Two Sum
- Sliding Window
- Two Pointers
- Prefix Sum
- Linked List Reverse / Cycle
- Tree DFS / BFS
- Heap / TopK
- Binary Search
- Graph DFS/BFS
- Topological Sort
- Backtracking
- Greedy
- 1D/2D DP
- Interval
- Monotonic Stack
- LRU

### P1 补充

- Trie
- Union Find
- Monotonic Queue
- Shortest Path
- LFU
- Bit Manipulation
- Difference Array
- Advanced String

## 31. 第二阶段：限时训练

开始做：

- 20 分钟：简单/中等单题
- 45 分钟：2 道题
- 60–90 分钟：小型笔试组合

必须模拟：

- 不看题解
- 不开 Copilot/Codex
- 自己处理输入输出
- 最后手动测试边界

## 32. 第三阶段：工程手撕

每周至少交替做：

- 1 个算法结构（LRU / heap / topo）
- 1 个 backend component（limiter / cache / queue）
- 1 个 AI Coding（tool / RAG / SSE）
- 1 组 SQL

---

# Part G：和本项目联动

## 33. 不要把刷题与项目分开

这个仓库本身就能成为 Coding 训练场：

- `src/rag_agent/retrieval/fusion.py`：学习排序、排名融合。
- `src/rag_agent/retrieval/hybrid.py`：学习集合、dict、TopK、结果合并。
- `src/rag_agent/agent/graph.py`：学习状态机、有界循环、失败恢复。
- `src/rag_agent/api/main.py`：学习 FastAPI、SSE、请求生命周期。
- `src/rag_agent/api/jobs.py`：理解当前内存任务状态为什么还不是 durable queue。
- `src/rag_agent/retrieval/sqlite_store.py`：学习 SQL、索引和存储边界。
- `tests/`：学习如何把边界条件写成可重复测试。

每学到一个面试主题，都问：

> “这个项目里有没有真实对应？如果有，代码在哪；如果没有，是应该实现，还是只需要学习？”

---

# Part H：掌握标准

## 34. 一道题怎样才算会

不是 AC 一次就算会。

至少满足：

- 能说出题型信号。
- 能先口述算法再编码。
- 不看答案写出核心代码。
- 能给复杂度。
- 能指出 2–3 个边界情况。
- 一周后还能复写。
- 能回答一个变化问题。

## 35. Agent Backend 面试准备完成的最低标准

### 算法

Hot100 主模式基本稳定，中等题能独立完成大部分。

### SQL

能现场写 Join、Group、Window、TopN，并解释索引和慢查询。

### Backend

能解释 Redis/MySQL/MQ/HTTP/SSE/concurrency，并能手撕 LRU、limiter、retry 等至少数个组件。

### AI Coding

能独立写 FastAPI + Tool Calling/RAG + timeout/retry + state 的最小系统。

### 项目

能从业务问题讲到架构、失败模式、指标、trade-off；不能只背 README。

### System Design

能把 Agent 服务拆成 API、state、orchestrator、tool、RAG、queue、storage、security、observability、eval，并说明为什么现在项目没有必要把所有模块都做成分布式系统。

---

# 36. 下一版待补

这份第一版已经明确训练体系，但还需要继续补成真正的大型教材：

- 按上述每种算法补完整题目编号与难度。
- 每类加入 3–5 道“识别题型”练习。
- 增加 ACM 输入输出模板。
- 增加完整 SQL 题组和答案。
- 增加 Backend Coding 可运行练习文件。
- 增加 AI Coding exercises 与自动测试。
- 按百度/字节/腾讯/阿里/美团等真实面经统计题型频率。
- 建立 `已学 / 能复写 / 需要复习` 的个人进度表，但不由程序自动宣称“已掌握”。

最终目标不是刷题数量，而是把算法、后端和 Agent 工程连接成同一套解决问题的能力。
