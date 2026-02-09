import type { TreeNode } from '../types';
import { deepCloneTree, validateAndNormalize } from './tree';

const STORAGE_KEY = 'mindmap-editor-data';

export function saveToLocalStorage(tree: TreeNode): void {
  try {
    const data = JSON.stringify(tree);
    localStorage.setItem(STORAGE_KEY, data);
  } catch {
    console.warn('LocalStorage 저장 실패');
  }
}

export function loadFromLocalStorage(): TreeNode | null {
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    if (!data) return null;
    const tree: TreeNode = JSON.parse(data);
    return validateAndNormalize(tree);
  } catch {
    console.warn('LocalStorage 복원 실패');
    return null;
  }
}

export function exportTreeAsJson(tree: TreeNode): string {
  return JSON.stringify(deepCloneTree(tree), null, 2);
}

export function importTreeFromJson(json: string): TreeNode {
  const parsed: TreeNode = JSON.parse(json);
  return validateAndNormalize(parsed);
}

export function downloadFile(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
