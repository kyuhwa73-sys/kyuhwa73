/** 마인드맵 트리 노드 */
export interface TreeNode {
  id: string;
  text: string;
  children: TreeNode[];
  collapsed?: boolean;
  style?: NodeStyle;
}

/** 노드 스타일 속성 */
export interface NodeStyle {
  backgroundColor?: string;
  borderColor?: string;
  fontSize?: number;
}

/** 스토어 상태 스냅샷 (undo/redo용) */
export interface MindMapSnapshot {
  tree: TreeNode;
  selectedNodeId: string | null;
}

/** 스토어 전체 상태 */
export interface MindMapState {
  tree: TreeNode;
  selectedNodeId: string | null;
  editingNodeId: string | null;

  // undo/redo
  past: MindMapSnapshot[];
  future: MindMapSnapshot[];

  // actions
  setTree: (tree: TreeNode) => void;
  setSelectedNodeId: (id: string | null) => void;
  setEditingNodeId: (id: string | null) => void;

  updateNodeText: (id: string, text: string) => void;
  updateNodeStyle: (id: string, style: Partial<NodeStyle>) => void;
  addChild: (parentId: string) => void;
  addSibling: (nodeId: string) => void;
  deleteNode: (nodeId: string) => void;
  toggleCollapse: (nodeId: string) => void;

  undo: () => void;
  redo: () => void;
  pushSnapshot: () => void;

  resetToNew: () => void;
  importTree: (tree: TreeNode) => void;
}
