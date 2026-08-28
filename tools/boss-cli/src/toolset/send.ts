import {
  randomIntInclusive,
  selectAllModifierKey,
  SEND_AFTER_ENTER_MS,
  SEND_INPUT_CLICK_MS,
  SEND_TYPING_GAP_MS,
  sleepRandom,
  typeTextWithRandomKeyDelay,
} from '../browser/index.js';
import type { Page } from 'puppeteer-core';
import { isBossChatIndexUrl } from '../common/auth.js';
import { withBossSessionPage } from '../common/boss_session_page.js';
import { runRequestAttachmentResume } from './action.js';
import { runOpenCandidateChat } from './chat.js';

export type SendChatMessageOptions = {
  text?: string;
  requestResume?: boolean;
  signal?: AbortSignal;
};

const SEQUENCE_MESSAGE_GAP_MS = { min: 1_000, max: 2_000 } as const;

export function validateMessageSequence(messages: string[]): [string, string, string] {
  if (messages.length !== 3) {
    throw new Error(`消息序列必须恰好三条，当前为 ${messages.length} 条。`);
  }
  const normalized = messages.map((message) => message.trim());
  if (normalized.some((message) => !message)) {
    throw new Error('消息序列中的消息不能为空。');
  }
  if (new Set(normalized).size !== normalized.length) {
    throw new Error('消息序列中的消息不能重复。');
  }
  return normalized as [string, string, string];
}

async function sendTextOnCurrentPage(
  page: Page,
  messageText: string,
  options: { signal?: AbortSignal; fastInput?: boolean } = {},
): Promise<void> {
  const signal = options.signal;
  if (!isBossChatIndexUrl(page.url())) {
    throw new Error('请先进入聊天列表页（/web/chat/index）并打开候选人聊天。');
  }

  const input = await page.$('#boss-chat-editor-input');
  if (!input) {
    throw new Error('未找到聊天输入框（#boss-chat-editor-input）。');
  }

  await input.click({
    delay: randomIntInclusive(SEND_INPUT_CLICK_MS.min, SEND_INPUT_CLICK_MS.max),
  });
  await sleepRandom(60, 220, signal);
  const selectAllMod = selectAllModifierKey();
  await page.keyboard.down(selectAllMod);
  await page.keyboard.press('KeyA');
  await page.keyboard.up(selectAllMod);
  await sleepRandom(45, 180, signal);
  await page.keyboard.press('Backspace');
  await sleepRandom(80, 260, signal);
  if (options.fastInput) {
    await page.keyboard.type(messageText, { delay: 0 });
  } else {
    await typeTextWithRandomKeyDelay(
      page,
      messageText,
      SEND_TYPING_GAP_MS.min,
      SEND_TYPING_GAP_MS.max,
      signal,
    );
  }
  await sleepRandom(120, 420, signal);
  await page.keyboard.press('Enter');
  await sleepRandom(SEND_AFTER_ENTER_MS.min, SEND_AFTER_ENTER_MS.max, signal);
}

async function assertExactCurrentChat(page: Page, name: string, job: string): Promise<void> {
  if (!isBossChatIndexUrl(page.url())) {
    throw new Error('当前不在沟通页，无法验证精确会话。');
  }
  const expectedNameLiteral = JSON.stringify(name);
  const expectedJobLiteral = JSON.stringify(job);
  const state = (await page.evaluate(`(() => {
    const expectedName = ${expectedNameLiteral};
    const expectedJob = ${expectedJobLiteral};
    const norm = (value) => (value ?? "").replace(/\\s+/g, " ").trim();
    const visible = (element) => {
      if (!element) return false;
      const rect = element.getBoundingClientRect();
      const style = window.getComputedStyle(element);
      return rect.width > 0 && rect.height > 0 && style.display !== "none" && style.visibility !== "hidden";
    };
    const selected = Array.from(document.querySelectorAll(".geek-item.selected")).find(visible);
    const detail = Array.from(document.querySelectorAll(".base-info-single-container")).find(visible);
    const selectedName = norm(selected?.querySelector(".geek-name")?.textContent);
    const detailName = norm(detail?.querySelector(".name-box")?.textContent);
    const communicationPosition = norm(detail?.querySelector(".position-item .position-name")?.textContent);
    return {
      valid:
        selectedName === expectedName &&
        detailName === expectedName &&
        communicationPosition.includes(expectedJob),
      selectedName,
      detailName,
      communicationPosition,
    };
  })()`)) as {
    valid: boolean;
    selectedName: string;
    detailName: string;
    communicationPosition: string;
  };
  if (!state.valid) {
    throw new Error(
      `精确会话验证失败：目标“${name} / ${job}”，当前“${state.selectedName || state.detailName || 'unknown'} / ${state.communicationPosition || 'unknown'}”。`,
    );
  }
}

async function countExactOutgoingMessage(page: Page, message: string): Promise<number> {
  const messageLiteral = JSON.stringify(message);
  return (await page.evaluate(`(() => {
    const expected = ${messageLiteral};
    const norm = (value) => (value ?? "").replace(/\\s+/g, " ").trim();
    return Array.from(document.querySelectorAll(".chat-message-list .message-item .item-myself .text span"))
      .filter((element) => norm(element.textContent) === expected)
      .length;
  })()`)) as number;
}

async function waitForNewExactOutgoingMessage(
  page: Page,
  message: string,
  previousCount: number,
): Promise<void> {
  const messageLiteral = JSON.stringify(message);
  const previousCountLiteral = JSON.stringify(previousCount);
  await page.waitForFunction(
    `(() => {
      const expected = ${messageLiteral};
      const previousCount = ${previousCountLiteral};
      const norm = (value) => (value ?? "").replace(/\\s+/g, " ").trim();
      const count = Array.from(document.querySelectorAll(".chat-message-list .message-item .item-myself .text span"))
        .filter((element) => norm(element.textContent) === expected)
        .length;
      return count > previousCount;
    })()`,
    { timeout: 10_000 },
  );
}

export async function runSendChatMessage(options: SendChatMessageOptions): Promise<string> {
  const messageText = (options.text ?? '').trim();
  const requestResume = options.requestResume ?? false;
  if (!messageText) {
    throw new Error('请指定 --text <消息> 或 -t <消息>。');
  }

  return withBossSessionPage(async (page) => {
    await sendTextOnCurrentPage(page, messageText, { signal: options.signal });
    if (!requestResume) {
      return `已发送消息：${messageText}`;
    }
    await sleepRandom(1200, 2800, options.signal);
    const resumeResult = await runRequestAttachmentResume(page);
    return `已发送消息：${messageText}\n${resumeResult}`;
  });
}

export type SendChatMessageSequenceOptions = {
  candidateName: string;
  jobKeyword: string;
  messages: string[];
  json?: boolean;
};

export async function runSendChatMessageSequence(
  options: SendChatMessageSequenceOptions,
): Promise<string> {
  const name = options.candidateName.trim();
  const job = options.jobKeyword.trim();
  const messages = validateMessageSequence(options.messages);
  if (!name || !job) {
    throw new Error('消息序列必须提供候选人姓名和岗位。');
  }

  return withBossSessionPage(async (page) => {
    await runOpenCandidateChat(page, name, true);
    let verified = 0;
    for (let index = 0; index < messages.length; index++) {
      const message = messages[index]!;
      await assertExactCurrentChat(page, name, job);
      const previousCount = await countExactOutgoingMessage(page, message);
      if (previousCount === 0) {
        await sendTextOnCurrentPage(page, message, { fastInput: true });
        await waitForNewExactOutgoingMessage(page, message, previousCount);
      }
      verified += 1;
      if (index < messages.length - 1) {
        await sleepRandom(SEQUENCE_MESSAGE_GAP_MS.min, SEQUENCE_MESSAGE_GAP_MS.max);
      }
    }
    if (options.json) {
      return JSON.stringify({ name, job, messagesVerified: verified });
    }
    return `已在精确会话中发送并验证 ${verified} 条消息。`;
  });
}
