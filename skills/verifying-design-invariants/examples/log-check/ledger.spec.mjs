// 与 examples/view-window 的模型同构：帐本有 n 条时，MaxLen = 1 的视图应显示几条。
// 日志校验器只认五个导出：initial / compared / loggedOnly / actions / rules。

const Wanted = (n) => (n === 0 ? 0 : 1);

export const initial = { count: 0, viewCount: 0, pc: "idle" };

// 规格能算出来的字段：每步都必须与日志一致
export const compared = ["count", "viewCount", "pc"];

// 规格不计算、只从日志取给规则用的字段（真实场景如 traceId、外部时间戳、别的进程写的标记）
export const loggedOnly = ["traceId"];

export const actions = {
  // 追加一条：写完帐本立刻把视图刷新到最新
  AppendLine: (state) => ({
    count: state.count + 1,
    viewCount: Wanted(state.count + 1),
    pc: "appended",
  }),
  // 进程重启：从帐本重建视图
  Rebuild: (state) => ({
    count: state.count,
    viewCount: Wanted(state.count),
    pc: "ready",
  }),
};

export const rules = {
  // 规则读的是日志记录的值，不是规格算出来的值
  ViewInSync: (s) => s.viewCount === Wanted(s.count),
  // 这条规则读的是 compared 之外的字段：规格算不出来，只能靠日志自己比
  TraceIdWellFormed: (s) => typeof s.traceId === "string" && s.traceId.length > 0,
};
