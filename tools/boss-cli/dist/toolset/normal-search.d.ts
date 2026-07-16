import type { Frame, Page } from 'puppeteer-core';
export declare function isBossChatSearchUrl(url: string): boolean;
export declare function assertNormalSearchPageReadyForPreview(page: Page): Promise<Frame>;
export declare function readNormalSearchSelectedJobLabel(frame: Frame): Promise<string>;
export declare function openNormalSearchResumePreview(frame: Frame, target: string): Promise<boolean>;
export declare function runNormalSearch(keyword?: string): Promise<string>;
//# sourceMappingURL=normal-search.d.ts.map