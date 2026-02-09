import { create } from 'zustand';
import type { MindMapState, MindMapSnapshot, TreeNode } from '../types';
import {
  createDefaultTree,
  deepCloneTree,
  updateText,
  updateStyle,
  addChildNode,
  addSiblingNode,
  deleteNodeFromTree,
  toggleCollapseNode,
  validateAndNormalize,
} from '../utils/tree';
import { loadFromLocalStorage, saveToLocalStorage } from '../utils/storage';
import type { NodeStyle } from '../types';

const MAX_HISTORY = 50;

function createSnapshot(state: { tree: TreeNode; selectedNodeId: string | null }): MindMapSnapshot {
  return {
    tree: deepCloneTree(state.tree),
    selectedNodeId: state.selectedNodeId,
  };
}

const initialTree = loadFromLocalStorage() || createDefaultTree();

export const useMindMapStore = create<MindMapState>((set, get) => ({
  tree: initialTree,
  selectedNodeId: null,
  editingNodeId: null,
  past: [],
  future: [],

  setTree: (tree: TreeNode) => {
    set({ tree });
    saveToLocalStorage(tree);
  },

  setSelectedNodeId: (id: string | null) => {
    set({ selectedNodeId: id });
  },

  setEditingNodeId: (id: string | null) => {
    set({ editingNodeId: id });
  },

  pushSnapshot: () => {
    const state = get();
    const snapshot = createSnapshot(state);
    set((s) => ({
      past: [...s.past.slice(-MAX_HISTORY + 1), snapshot],
      future: [],
    }));
  },

  updateNodeText: (id: string, text: string) => {
    const state = get();
    const newTree = updateText(state.tree, id, text);
    set({ tree: newTree });
    saveToLocalStorage(newTree);
  },

  updateNodeStyle: (id: string, style: Partial<NodeStyle>) => {
    const state = get();
    state.pushSnapshot();
    const newTree = updateStyle(state.tree, id, style);
    set({ tree: newTree });
    saveToLocalStorage(newTree);
  },

  addChild: (parentId: string) => {
    const state = get();
    state.pushSnapshot();
    const result = addChildNode(state.tree, parentId);
    set({ tree: result.tree, selectedNodeId: result.newId, editingNodeId: result.newId });
    saveToLocalStorage(result.tree);
  },

  addSibling: (nodeId: string) => {
    const state = get();
    const result = addSiblingNode(state.tree, nodeId);
    if (!result) return; // Root에는 형제 추가 불가
    state.pushSnapshot();
    set({ tree: result.tree, selectedNodeId: result.newId, editingNodeId: result.newId });
    saveToLocalStorage(result.tree);
  },

  deleteNode: (nodeId: string) => {
    const state = get();
    if (state.tree.id === nodeId) return; // Root 삭제 금지
    state.pushSnapshot();
    const newTree = deleteNodeFromTree(state.tree, nodeId);
    if (!newTree) return;
    set({
      tree: newTree,
      selectedNodeId: state.tree.id, // Root로 선택 이동
      editingNodeId: null,
    });
    saveToLocalStorage(newTree);
  },

  toggleCollapse: (nodeId: string) => {
    const state = get();
    state.pushSnapshot();
    const newTree = toggleCollapseNode(state.tree, nodeId);
    set({ tree: newTree });
    saveToLocalStorage(newTree);
  },

  undo: () => {
    const state = get();
    if (state.past.length === 0) return;
    const current = createSnapshot(state);
    const prev = state.past[state.past.length - 1];
    set({
      tree: prev.tree,
      selectedNodeId: prev.selectedNodeId,
      editingNodeId: null,
      past: state.past.slice(0, -1),
      future: [current, ...state.future].slice(0, MAX_HISTORY),
    });
    saveToLocalStorage(prev.tree);
  },

  redo: () => {
    const state = get();
    if (state.future.length === 0) return;
    const current = createSnapshot(state);
    const next = state.future[0];
    set({
      tree: next.tree,
      selectedNodeId: next.selectedNodeId,
      editingNodeId: null,
      past: [...state.past, current].slice(-MAX_HISTORY),
      future: state.future.slice(1),
    });
    saveToLocalStorage(next.tree);
  },

  resetToNew: () => {
    const state = get();
    state.pushSnapshot();
    const newTree = createDefaultTree();
    set({ tree: newTree, selectedNodeId: null, editingNodeId: null });
    saveToLocalStorage(newTree);
  },

  importTree: (tree: TreeNode) => {
    const state = get();
    state.pushSnapshot();
    const validated = validateAndNormalize(tree);
    set({ tree: validated, selectedNodeId: null, editingNodeId: null });
    saveToLocalStorage(validated);
  },
}));
