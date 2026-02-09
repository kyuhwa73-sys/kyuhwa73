import type { Node, Edge } from '@xyflow/react';
import type { TreeNode, NodeStyle } from '../types';

// ─── ID 생성 ───────────────────────────────────────────────
let idCounter = Date.now();
export function generateId(): string {
  return `node_${++idCounter}`;
}

// ─── 기본 트리 (샘플) ──────────────────────────────────────
export function createDefaultTree(): TreeNode {
  return {
    id: generateId(),
    text: '중심 주제',
    children: [
      {
        id: generateId(),
        text: '가지 1',
        children: [
          { id: generateId(), text: '세부 1-1', children: [] },
          { id: generateId(), text: '세부 1-2', children: [] },
        ],
      },
      {
        id: generateId(),
        text: '가지 2',
        children: [
          { id: generateId(), text: '세부 2-1', children: [] },
        ],
      },
      {
        id: generateId(),
        text: '가지 3',
        children: [],
      },
    ],
  };
}

// ─── 샘플 트리 데이터 ──────────────────────────────────────
export function createSampleTree(): TreeNode {
  return {
    id: generateId(),
    text: '프로젝트 계획',
    children: [
      {
        id: generateId(),
        text: '기획',
        children: [
          { id: generateId(), text: '시장 조사', children: [] },
          { id: generateId(), text: '요구사항 분석', children: [] },
          { id: generateId(), text: '일정 수립', children: [] },
        ],
      },
      {
        id: generateId(),
        text: '디자인',
        children: [
          { id: generateId(), text: 'UI/UX 설계', children: [] },
          { id: generateId(), text: '프로토타입', children: [] },
        ],
      },
      {
        id: generateId(),
        text: '개발',
        children: [
          { id: generateId(), text: '프론트엔드', children: [
            { id: generateId(), text: 'React', children: [] },
            { id: generateId(), text: 'TypeScript', children: [] },
          ] },
          { id: generateId(), text: '백엔드', children: [
            { id: generateId(), text: 'API 설계', children: [] },
            { id: generateId(), text: '데이터베이스', children: [] },
          ] },
        ],
      },
      {
        id: generateId(),
        text: '테스트 및 배포',
        children: [
          { id: generateId(), text: 'QA', children: [] },
          { id: generateId(), text: '배포 자동화', children: [] },
        ],
      },
    ],
  };
}

// ─── 깊은 복사 ─────────────────────────────────────────────
export function deepCloneTree(node: TreeNode): TreeNode {
  return {
    id: node.id,
    text: node.text,
    collapsed: node.collapsed,
    style: node.style ? { ...node.style } : undefined,
    children: node.children.map(deepCloneTree),
  };
}

// ─── 트리에서 노드 검색 ────────────────────────────────────
export function findNode(tree: TreeNode, id: string): TreeNode | null {
  if (tree.id === id) return tree;
  for (const child of tree.children) {
    const found = findNode(child, id);
    if (found) return found;
  }
  return null;
}

// ─── 부모 노드 검색 ────────────────────────────────────────
export function findParent(tree: TreeNode, id: string): TreeNode | null {
  for (const child of tree.children) {
    if (child.id === id) return tree;
    const found = findParent(child, id);
    if (found) return found;
  }
  return null;
}

// ─── 노드 텍스트 업데이트 ──────────────────────────────────
export function updateText(tree: TreeNode, id: string, text: string): TreeNode {
  if (tree.id === id) return { ...tree, text };
  return {
    ...tree,
    children: tree.children.map((c) => updateText(c, id, text)),
  };
}

// ─── 노드 스타일 업데이트 ──────────────────────────────────
export function updateStyle(tree: TreeNode, id: string, style: Partial<NodeStyle>): TreeNode {
  if (tree.id === id) {
    return { ...tree, style: { ...tree.style, ...style } };
  }
  return {
    ...tree,
    children: tree.children.map((c) => updateStyle(c, id, style)),
  };
}

// ─── 자식 추가 ─────────────────────────────────────────────
export function addChildNode(tree: TreeNode, parentId: string): { tree: TreeNode; newId: string } {
  const newId = generateId();
  const newChild: TreeNode = { id: newId, text: '새 노드', children: [] };

  function insert(node: TreeNode): TreeNode {
    if (node.id === parentId) {
      return { ...node, collapsed: false, children: [...node.children, newChild] };
    }
    return { ...node, children: node.children.map(insert) };
  }

  return { tree: insert(tree), newId };
}

// ─── 형제 추가 ─────────────────────────────────────────────
export function addSiblingNode(tree: TreeNode, nodeId: string): { tree: TreeNode; newId: string } | null {
  // Root에는 형제 추가 불가
  if (tree.id === nodeId) return null;

  const newId = generateId();
  const newSibling: TreeNode = { id: newId, text: '새 노드', children: [] };

  function insert(node: TreeNode): TreeNode {
    const idx = node.children.findIndex((c) => c.id === nodeId);
    if (idx !== -1) {
      const newChildren = [...node.children];
      newChildren.splice(idx + 1, 0, newSibling);
      return { ...node, children: newChildren };
    }
    return { ...node, children: node.children.map(insert) };
  }

  return { tree: insert(tree), newId };
}

// ─── 노드 삭제 (자식 포함, Root 삭제 금지) ────────────────
export function deleteNodeFromTree(tree: TreeNode, nodeId: string): TreeNode | null {
  if (tree.id === nodeId) return null; // Root는 삭제 금지

  function remove(node: TreeNode): TreeNode {
    return {
      ...node,
      children: node.children
        .filter((c) => c.id !== nodeId)
        .map(remove),
    };
  }

  return remove(tree);
}

// ─── 접기/펼치기 토글 ──────────────────────────────────────
export function toggleCollapseNode(tree: TreeNode, nodeId: string): TreeNode {
  if (tree.id === nodeId) {
    return { ...tree, collapsed: !tree.collapsed };
  }
  return {
    ...tree,
    children: tree.children.map((c) => toggleCollapseNode(c, nodeId)),
  };
}

// ─── 모든 ID 수집 (중복 검사용) ────────────────────────────
export function collectIds(node: TreeNode): Set<string> {
  const ids = new Set<string>();
  function walk(n: TreeNode) {
    if (ids.has(n.id)) {
      // 중복 ID 발견 시 새 ID 부여
      n.id = generateId();
    }
    ids.add(n.id);
    n.children.forEach(walk);
  }
  walk(node);
  return ids;
}

// ─── 순환 참조 검사 ────────────────────────────────────────
export function hasCycle(node: TreeNode, visited = new Set<string>()): boolean {
  if (visited.has(node.id)) return true;
  visited.add(node.id);
  for (const child of node.children) {
    if (hasCycle(child, new Set(visited))) return true;
  }
  return false;
}

// ─── 트리를 검증하고 정규화 ────────────────────────────────
export function validateAndNormalize(tree: TreeNode): TreeNode {
  const clone = deepCloneTree(tree);
  collectIds(clone); // 중복 ID 수정
  if (hasCycle(clone)) {
    throw new Error('순환 참조가 감지되었습니다.');
  }
  return clone;
}

// ─── 노드 깊이 계산 ────────────────────────────────────────
export function getDepth(tree: TreeNode, nodeId: string, depth = 0): number {
  if (tree.id === nodeId) return depth;
  for (const child of tree.children) {
    const d = getDepth(child, nodeId, depth + 1);
    if (d !== -1) return d;
  }
  return -1;
}

// ─── 깊이별 색상 팔레트 ────────────────────────────────────
const DEPTH_COLORS = [
  '#4A90D9', // 0 - root (blue)
  '#50C878', // 1 - green
  '#FF8C42', // 2 - orange
  '#9B59B6', // 3 - purple
  '#E74C3C', // 4 - red
  '#1ABC9C', // 5 - teal
  '#F39C12', // 6 - yellow
  '#3498DB', // 7 - light blue
];

export function getColorForDepth(depth: number): string {
  return DEPTH_COLORS[depth % DEPTH_COLORS.length];
}

// ─── Tree → React Flow Nodes/Edges 변환 ────────────────────
export interface FlowData {
  nodes: Node[];
  edges: Edge[];
}

export function treeToFlow(
  tree: TreeNode,
  selectedNodeId: string | null,
  editingNodeId: string | null,
): FlowData {
  const nodes: Node[] = [];
  const edges: Edge[] = [];

  function walk(node: TreeNode, depth: number) {
    const bgColor = node.style?.backgroundColor || getColorForDepth(depth);
    const borderColor = node.style?.borderColor || getColorForDepth(depth);
    const fontSize = node.style?.fontSize || (depth === 0 ? 18 : 14);

    nodes.push({
      id: node.id,
      type: 'mindMapNode',
      position: { x: 0, y: 0 }, // dagre가 재배치
      data: {
        text: node.text,
        isRoot: depth === 0,
        isSelected: node.id === selectedNodeId,
        isEditing: node.id === editingNodeId,
        collapsed: !!node.collapsed,
        hasChildren: node.children.length > 0,
        depth,
        style: {
          backgroundColor: bgColor,
          borderColor,
          fontSize,
        },
      },
    });

    if (!node.collapsed) {
      for (const child of node.children) {
        edges.push({
          id: `e-${node.id}-${child.id}`,
          source: node.id,
          target: child.id,
          type: 'smoothstep',
          style: { stroke: getColorForDepth(depth), strokeWidth: 2 },
          animated: false,
        });
        walk(child, depth + 1);
      }
    }
  }

  walk(tree, 0);
  return { nodes, edges };
}

// ─── React Flow → Tree 변환 (flowToTree) ───────────────────
export function flowToTree(nodes: Node[], edges: Edge[]): TreeNode | null {
  if (nodes.length === 0) return null;

  // 루트 노드 찾기 (isRoot 또는 부모 엣지가 없는 노드)
  const childIds = new Set(edges.map((e) => e.target));
  const rootNode = nodes.find((n) => !childIds.has(n.id)) || nodes[0];

  function buildSubtree(nodeId: string): TreeNode {
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return { id: nodeId, text: '', children: [] };

    const childEdges = edges.filter((e) => e.source === nodeId);
    return {
      id: node.id,
      text: (node.data as Record<string, unknown>).text as string || '',
      collapsed: (node.data as Record<string, unknown>).collapsed as boolean || false,
      style: (node.data as Record<string, unknown>).style as NodeStyle | undefined,
      children: childEdges.map((e) => buildSubtree(e.target)),
    };
  }

  return buildSubtree(rootNode.id);
}
