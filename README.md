# 마인드맵 편집기 (Mind Map Editor)

React Flow + dagre 기반의 Top-Down 마인드맵 편집기입니다.

## 주요 기능

- **Top-Down 트리 레이아웃**: 루트 노드가 상단 중앙에 위치하고 하위 노드가 아래로 확장
- **노드 편집**: 더블클릭 또는 F2로 텍스트 편집, Esc로 취소
- **노드 추가/삭제**: Tab(자식 추가), Enter(형제 추가), Delete(삭제)
- **접기/펼치기**: 노드 하단의 +/- 버튼으로 자식 노드 숨기기/보이기
- **자동 레이아웃**: dagre 엔진으로 균형 잡힌 트리 배치
- **실행 취소/다시 실행**: 스냅샷 기반 Undo/Redo (Ctrl+Z / Ctrl+Y)
- **자동 저장**: LocalStorage에 자동 저장, 앱 로드 시 자동 복원
- **JSON 가져오기/내보내기**: 마인드맵 데이터를 JSON 파일로 관리
- **PNG 내보내기**: 현재 마인드맵을 이미지로 내보내기
- **인쇄 기능**: 마인드맵을 인쇄
- **노드 스타일링**: 배경색, 테두리색, 글자 크기 커스터마이징
- **미니맵**: 전체 마인드맵 구조를 미니맵으로 확인
- **한국어 UI**: 모든 메뉴와 안내가 한국어로 표시

## 기술 스택

- **Vite** + **React** + **TypeScript**
- **@xyflow/react** (React Flow) - 노드/엣지 시각화, 줌/팬
- **dagre** - 자동 트리 레이아웃 (rankdir="TB")
- **Zustand** - 상태 관리
- **html-to-image** - PNG 내보내기

## 설치 및 실행

```bash
# 의존성 설치
npm install

# 개발 서버 실행
npm run dev

# 빌드
npm run build

# 빌드된 결과물 미리보기
npm run preview
```

## 프로젝트 구조

```
src/
├── types/
│   └── index.ts          # TypeScript 타입 정의 (TreeNode, NodeStyle 등)
├── utils/
│   ├── tree.ts           # 트리 유틸리티 (treeToFlow, flowToTree, CRUD 등)
│   ├── layout.ts         # dagre 레이아웃 (applyLayout)
│   └── storage.ts        # LocalStorage, JSON Import/Export
├── store/
│   └── useMindMapStore.ts # Zustand 스토어 (상태 + undo/redo)
├── components/
│   ├── MindMapEditor.tsx  # 메인 에디터 (React Flow + 키보드 단축키)
│   ├── MindMapNode.tsx    # 커스텀 노드 컴포넌트
│   ├── Toolbar.tsx        # 상단 툴바
│   └── PropertiesPanel.tsx # 우측 속성 패널
├── App.tsx               # 앱 엔트리 (ReactFlowProvider)
├── main.tsx              # React DOM 렌더링
└── index.css             # 전체 스타일
```

## 핵심 유틸리티

### (a) `treeToFlow(tree, selectedNodeId, editingNodeId)`
트리 데이터를 React Flow의 nodes/edges 배열로 변환합니다.

### (b) `flowToTree(nodes, edges)`
React Flow의 nodes/edges를 다시 트리 구조로 역변환합니다.

### (c) `applyLayout(nodes, edges)`
dagre를 사용하여 TB(Top-Bottom) 방향으로 자동 레이아웃을 적용합니다.

## 키보드 단축키

| 단축키 | 동작 |
|--------|------|
| `Tab` | 선택된 노드에 자식 추가 |
| `Enter` | 선택된 노드에 형제 추가 |
| `Delete` / `Backspace` | 선택된 노드 삭제 (루트 제외) |
| `F2` / 더블클릭 | 노드 텍스트 편집 |
| `Esc` | 편집 취소 / 선택 해제 |
| `Space` | 접기/펼치기 토글 |
| `Ctrl+Z` | 실행 취소 |
| `Ctrl+Y` / `Ctrl+Shift+Z` | 다시 실행 |
| `Ctrl+S` | 저장 |
| `Ctrl+P` | 인쇄 |

## 샘플 데이터

`src/utils/tree.ts`의 `createSampleTree()` 함수에서 테스트용 샘플 트리 데이터를 확인할 수 있습니다. "프로젝트 계획" 주제의 다중 계층 마인드맵 예시가 포함되어 있습니다.
