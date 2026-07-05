import type { Page } from 'puppeteer-core';
/**
 * 全屏半透明彩虹蒙层（呼吸式明暗脉冲），文案视口居中；`pointer-events: none` 不拦截页面点击与自动化操作。
 * 与 {@link hideAgentOperatingIndicator} 成对使用。
 * 品牌标识取自 `BOSS_CLI_AGENT_BRAND` 环境变量（未设置或为空时使用 `boss-cli`）。
 */
export declare function showAgentOperatingIndicator(page: Page): Promise<void>;
/** 移除 {@link showAgentOperatingIndicator} 注入的样式与全屏蒙层（幂等）。 */
export declare function hideAgentOperatingIndicator(page: Page): Promise<void>;
//# sourceMappingURL=agent_operating_indicator.d.ts.map