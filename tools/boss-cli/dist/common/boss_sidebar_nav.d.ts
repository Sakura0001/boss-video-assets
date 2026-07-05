import type { Page } from 'puppeteer-core';
/**
 * 点击 Boss 左侧 `.menu-list` 中的菜单项，并等待导航到给定 pathname（如 `/web/chat/index`）。
 */
export declare function clickBossSidebarMenuToPath(page: Page, menuLabel: string, targetPath: string): Promise<void>;
//# sourceMappingURL=boss_sidebar_nav.d.ts.map