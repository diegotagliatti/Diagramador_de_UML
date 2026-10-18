# Diagramador_de_UML
O PyDiagram é um editor visual de diagramas UML construído inteiramente em Python e PyQt6. O seu objetivo principal é permitir que qualquer utilizador consiga desenhar, organizar e editar diagramas de classes de forma rápida e interativa, funcionando como uma aplicação de ambiente de trabalho totalmente independente e sem necessidade de internet


# PyDiagram

Aplicativo desktop open-source para modelagem e diagramação UML, inspirado no StarUML e desenvolvido exclusivamente em **Python** com **PyQt6**.

---

## Estrutura do Projeto

```
diagrama/
├── venv/                       # Ambiente virtual Python
├── locales/                    # Arquivos de tradução (i18n)
│   ├── pt-BR.json              # Português do Brasil
│   └── en-US.json              # Inglês (EUA)
├── requirements.txt            # Dependências fixadas (PyQt6)
├── uml_items.py                # Itens gráficos UML (Classes, Membros, Conexões, Painel Flutuante)
├── ui_components.py            # Componentes visuais otimizados (Scene, DiagramView, MinimapView)
├── main.py                     # Janela principal (MainWindow), orquestração e ponto de entrada
└── README.md                   # Documentação do projeto
```

---

## Funcionalidades Implementadas

1. **Interface Moderna com Splitters & Barra Lateral**:
   - Layout redimensionável com `QSplitter` horizontal principal (Barra Lateral à esquerda e Canvas à direita).
   - Barra lateral organizada com `QSplitter` vertical contendo:
     - **Explorador de Modelos (**`QTreeWidget`**)**: Visão em árvore de todas as classes, atributos e métodos com seleção sincronizada.
     - **Painel de Propriedades (**`QGroupBox 'Properties'`**)**: Editor integrado via `QFormLayout` que sincroniza bidirecionalmente com o item selecionado no diagrama ou na árvore:
       - **name**: `QLineEdit` para edição de nome em tempo real.
       - **visibility**: `QComboBox` com opções `public (+)`, `private (-)`, `protected (#)` e `none`.
       - **isAbstract**: `QCheckBox` para ligar/desligar o estilo itálico (abstração).
       - Desabilita automaticamente todos os campos quando nada estiver selecionado.
2. **Canvas Interativo (**`QGraphicsView` **&** `QGraphicsScene`**)**:
   - Malha de pontos quadriculada suave no fundo (estilo StarUML / Figma).
   - Zoom in / Zoom out interativo com a roda do mouse.
   - Seleção em área retangular com o mouse.
3. **Classes UML com 3 Compartimentos & Menus de Contexto (**`DiagramNodeItem`**,** `EditableTextItem`**)**:
   - Dividido nos 3 compartimentos clássicos de UML: **Título/Classe**, **Atributos** e **Operações/Métodos**.
   - **Menu de Contexto da Classe (Botão direito na área geral)**:
     - `"Add Atributo"`: Adiciona nova linha editável no compartimento de atributos.
     - `"add método"`: Adiciona nova linha editável no compartimento de métodos/operações.
     - `"Classe Abstrata"` (marcar/desmarcar): Aplica estilo **Negrito E Itálico** no título da classe ou remove itálico ao desmarcar.
   - **Menu de Contexto do Membro (Botão direito em atributo ou método)**:
     - Ativa o destaque visual (seleção/foco) na linha selecionada.
     - `"Tornar Público (+)"`: Substitui ou adiciona o modificador `+ `no início do membro.
     - `"Tornar Privado (-)"`: Substitui ou adiciona o modificador `- `no início do membro.
     - `"Tornar Protegido (#)"`: Substitui ou adiciona o modificador `# `no início do membro.
     - `"mudar para abstrato (itálico)"`: Alterna o estilo itálico exclusivamente para aquela linha.
     - `"Remover"`: Remove o membro da classe.
   - **Edição Individual (Duplo clique) & Formatação Inteligente**:
     - Abre o modo de edição exclusivo em qualquer linha individual (título, atributo ou método).
     - `item_type='title'`: Normaliza acentos e cedilhas (`unicodedata`), remove caracteres especiais e espaços, aplica PascalCase e negrito (ex: `"tasças"` $\rightarrow$ `"Tascas"`).
     - `item_type='attribute'`: Verifica modificadores (`+`, `-`, `#`, `~`). Se não possuir, prefixa automaticamente com `+ `(ex: `"teste"` $\rightarrow$ `"+ teste"`).
     - `item_type='method'`: Garante modificador de visibilidade e fecha com parênteses caso não termine com `)` (ex: `"teste"` $\rightarrow$ `"+ teste()"`).
   - **Painel Flutuante de Ações Rápidas (**`InlineActionPanel`**)**:
     - Acompanha o item de atributo ou método durante a edição ou seleção.
     - `↑` **e** `↓` **(Mover)**: Reordena os membros trocando de posição com o item anterior ou posterior.
     - `+` **(Adicionar)**: Insere um novo atributo (`+ novoItem: tipo`) ou método (`+ novoMetodo()`) logo após a linha atual, atualiza a cena, redimensiona a classe e abre a edição imediatamente.
     - `-` **(Remover)**: Remove o membro da lista interna e da cena, fecha o painel flutuante e recalcula o tamanho do nó.
   - **Auto-Redimensionamento Dinâmico**: O nó recalcula sua largura e as alturas dos 3 compartimentos conforme o texto digitado, atualizando as linhas conectadas em tempo real.
4. **Conexões de Herança UML (**`DiagramConnectionItem`**)**:
   - **Cálculo de Borda a Borda**: Não desenha do centro para o centro. Utiliza `QLineF` e cálculo de interseção (`intersect()`) com o `sceneBoundingRect()` de cada nó, garantindo que a linha comece e termine com exatidão nas bordas visíveis das classes.
   - **Seta de Herança (Generalização UML)**: Desenha na extremidade da classe Pai (destino) um triângulo fechado (`QPolygonF`) com interior branco/vazio e contornos visíveis, conforme a especificação UML.
   - **Rastreamento em Tempo Real**: Conexões atualizam suas extremidades e orientação instantaneamente quando qualquer nó é arrastado ou redimensionado.
5. **Internacionalização (i18n)**:
   - Troca dinâmica em tempo de execução entre **Português (pt-BR)** e **Inglês (en-US)** pelo menu `Idioma`.
6. **Exportação de Imagem**:
   - Exportação em alta fidelidade para formatos `.png` e `.jpg`.
   - Atalho `Ctrl+E` e disponível tanto no menu `Arquivo` quanto na barra de ferramentas.
   - Renderização isolada do conteúdo com enquadramento dinâmico (`itemsBoundingRect`) e fundo limpo.

---

## Como Executar

### 1. Abrir o terminal no diretório do projeto:

```powershell
Ir pasta onde foi baixado"
```

### 2. Ativar o Ambiente Virtual (venv):

* **No PowerShell:**

  ```powershell
  .\venv\Scripts\Activate.ps1
  ```

  *(Se sua política de execução restringir scripts, execute* `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` *ou use o Command Prompt)*
* **No Prompt de Comando (CMD):**

  ```cmd
  venv\Scripts\activate.bat
  ```

### 3. Rodar a Aplicação:

```powershell
python main.py
```
### Opção 2: Versões Instaláveis Pré-Compiladas

Caso prefira não configurar o Python no seu computador, disponibilizamos versões prontas a usar (standalone) na aba **Releases** deste repositório:

* **Windows:** Executável portátil (.exe)
* **Linux (Debian/Ubuntu/Mint):** Pacote de instalação (.deb)
* **Linux (Fedora/RedHat):** Pacote de instalação (.rpm)

> **Aviso de Estabilidade:** Estas versões pré-compiladas facilitam o acesso, mas o processo de empacotamento pode introduzir bugs ocasionais ou comportamentos inesperados na interface.
