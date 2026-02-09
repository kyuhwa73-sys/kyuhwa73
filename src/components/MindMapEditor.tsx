import { useCallback, useEffect, useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useReactFlow,
  type NodeMouseHandler,
  type OnSelectionChangeFunc,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import MindMapNodeComponent from './MindMapNode';
import Toolbar from './Toolbar';
import PropertiesPanel from './PropertiesPanel';
import { useMindMapStore } from '../store/useMindMapStore';
import { treeToFlow } from '../utils/tree';
import { applyLayout } from '../utils/layout';
import { exportTreeAsJson } from '../utils/storage';
import { toPng } from 'html-to-image';

const nodeTypes = {
  mindMapNode: MindMapNodeComponent,
};

export default function MindMapEditor() {
  const {
    tree,
    selectedNodeId,
    editingNodeId,
    setSelectedNodeId,
    setEditingNodeId,
    addChild,
    addSibling,
    deleteNode,
    toggleCollapse,
    undo,
    redo,
  } = useMindMapStore();

  const { fitView } = useReactFlow();

  // 트리 → Flow 변환 + dagre 레이아웃
  const { nodes, edges } = useMemo(() => {
    const flow = treeToFlow(tree, selectedNodeId, editingNodeId);
    const layoutNodes = applyLayout(flow.nodes, flow.edges);
    return { nodes: layoutNodes, edges: flow.edges };
  }, [tree, selectedNodeId, editingNodeId]);

  // 레이아웃 변경 시 fitView
  useEffect(() => {
    const timer = setTimeout(() => {
      fitView({ padding: 0.15, duration: 200 });
    }, 50);
    return () => clearTimeout(timer);
  }, [nodes.length, fitView]);

  // 노드 클릭 핸들러
  const onNodeClick: NodeMouseHandler = useCallback(
    (_event, node) => {
      setSelectedNodeId(node.id);
    },
    [setSelectedNodeId],
  );

  // 선택 변경
  const onSelectionChange: OnSelectionChangeFunc = useCallback(
    ({ nodes: selectedNodes }) => {
      if (selectedNodes.length === 0) {
        // 빈 영역 클릭 시 선택 해제하지 않음 (UX 개선)
      } else {
        setSelectedNodeId(selectedNodes[0].id);
      }
    },
    [setSelectedNodeId],
  );

  // 캔버스 클릭 (빈 영역)
  const onPaneClick = useCallback(() => {
    if (editingNodeId) {
      setEditingNodeId(null);
    }
  }, [editingNodeId, setEditingNodeId]);

  // 키보드 단축키
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // 편집 중이면 노드 편집 관련 키만 처리 (MindMapNode에서 처리)
      if (editingNodeId) return;

      // input, textarea 등에 포커스가 있으면 무시
      const target = e.target as HTMLElement;
      if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;

      // Ctrl/Cmd 조합
      if (e.ctrlKey || e.metaKey) {
        switch (e.key.toLowerCase()) {
          case 'z':
            e.preventDefault();
            if (e.shiftKey) {
              redo();
            } else {
              undo();
            }
            return;
          case 'y':
            e.preventDefault();
            redo();
            return;
          case 's':
            e.preventDefault();
            // 저장 (autosave이므로 확인 메시지만)
            {
              const json = exportTreeAsJson(tree);
              localStorage.setItem('mindmap-editor-data', JSON.stringify(JSON.parse(json)));
              // 간단한 시각적 피드백
              const el = document.querySelector('.toolbar-btn[title*="저장"]');
              if (el) {
                el.classList.add('flash');
                setTimeout(() => el.classList.remove('flash'), 300);
              }
            }
            return;
          case 'p':
            e.preventDefault();
            // 인쇄
            {
              const flowEl = document.querySelector('.react-flow') as HTMLElement;
              if (!flowEl) return;
              toPng(flowEl, { backgroundColor: '#ffffff', quality: 1, pixelRatio: 2 })
                .then((dataUrl) => {
                  const printWindow = window.open('', '_blank');
                  if (!printWindow) return;
                  printWindow.document.write(`
                    <!DOCTYPE html><html><head><title>마인드맵 인쇄</title>
                    <style>body{margin:0;display:flex;justify-content:center;align-items:center;min-height:100vh}img{max-width:100%;height:auto}@media print{body{margin:0}img{max-width:100%;page-break-inside:avoid}}</style>
                    </head><body><img src="${dataUrl}" /></body></html>
                  `);
                  printWindow.document.close();
                  printWindow.onload = () => printWindow.print();
                });
            }
            return;
        }
      }

      if (!selectedNodeId) return;

      switch (e.key) {
        case 'Tab':
          e.preventDefault();
          addChild(selectedNodeId);
          break;
        case 'Enter':
          e.preventDefault();
          addSibling(selectedNodeId);
          break;
        case 'Delete':
        case 'Backspace':
          e.preventDefault();
          if (tree.id !== selectedNodeId) {
            deleteNode(selectedNodeId);
          }
          break;
        case 'F2':
          e.preventDefault();
          setEditingNodeId(selectedNodeId);
          break;
        case ' ':
          e.preventDefault();
          toggleCollapse(selectedNodeId);
          break;
        case 'Escape':
          e.preventDefault();
          setSelectedNodeId(null);
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    selectedNodeId,
    editingNodeId,
    tree,
    addChild,
    addSibling,
    deleteNode,
    toggleCollapse,
    undo,
    redo,
    setSelectedNodeId,
    setEditingNodeId,
  ]);

  return (
    <div className="mindmap-editor">
      <Toolbar />
      <div className="editor-content">
        <div className="flow-container">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodeClick={onNodeClick}
            onSelectionChange={onSelectionChange}
            onPaneClick={onPaneClick}
            fitView
            fitViewOptions={{ padding: 0.15 }}
            minZoom={0.1}
            maxZoom={2}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable
            selectNodesOnDrag={false}
            proOptions={{ hideAttribution: true }}
          >
            <Background color="#334155" gap={20} />
            <Controls position="bottom-left" />
            <MiniMap
              position="bottom-right"
              nodeColor={(node) => {
                const data = node.data as Record<string, unknown>;
                const style = data?.style as Record<string, string> | undefined;
                return style?.backgroundColor || '#4A90D9';
              }}
              maskColor="rgba(0, 0, 0, 0.3)"
              style={{ backgroundColor: '#1e293b' }}
            />
          </ReactFlow>
        </div>
        <PropertiesPanel />
      </div>
    </div>
  );
}
