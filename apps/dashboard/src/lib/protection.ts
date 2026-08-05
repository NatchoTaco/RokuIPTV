export type ChannelProtectionState = {
  protected_from_auto_merge: boolean;
};

export type DuplicateClusterProtectionState = {
  review_status: string;
};

export const visibilityFilterOptions = ["visible", "hidden", "always_visible", "protected"] as const;

export function channelProtectionActionLabel(channel: ChannelProtectionState): "Protect" | "Unprotect" {
  return channel.protected_from_auto_merge ? "Unprotect" : "Protect";
}

export function nextChannelProtectionState(channel: ChannelProtectionState): boolean {
  return !channel.protected_from_auto_merge;
}

export function duplicateProtectionActionLabel(cluster: DuplicateClusterProtectionState): "Protect" | "Unprotect" {
  return cluster.review_status === "protected" ? "Unprotect" : "Protect";
}

export function duplicateProtectionAction(cluster: DuplicateClusterProtectionState): "protect" | "unprotect" {
  return cluster.review_status === "protected" ? "unprotect" : "protect";
}

export function clearProtectionsConfirmation(totalProtectionCount: number): string {
  return `Clear ${totalProtectionCount.toLocaleString()} manual protection override(s)? This only removes protection overrides and preserves Allow/Hide visibility decisions.`;
}
