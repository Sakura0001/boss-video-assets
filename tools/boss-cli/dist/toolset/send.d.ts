export type SendChatMessageOptions = {
    text?: string;
    requestResume?: boolean;
    signal?: AbortSignal;
};
export declare function validateMessageSequence(messages: string[]): [string, string, string];
export declare function runSendChatMessage(options: SendChatMessageOptions): Promise<string>;
export type SendChatMessageSequenceOptions = {
    candidateName: string;
    jobKeyword: string;
    messages: string[];
    json?: boolean;
};
export declare function runSendChatMessageSequence(options: SendChatMessageSequenceOptions): Promise<string>;
//# sourceMappingURL=send.d.ts.map