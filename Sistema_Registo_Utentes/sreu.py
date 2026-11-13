"""
SISTEMA DE REGISTO ELETRÓNICO DE UTENTES
Projeto académico demonstrativo — Python + Tkinter + SQLite

AVISO:
- Utilize apenas dados fictícios durante o desenvolvimento e a demonstração.
- Esta versão é uma base académica, não um sistema clínico certificado.
- Antes de utilização real são necessárias avaliação de segurança, cópias
  de segurança, políticas institucionais e conformidade legal.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import hashlib
import secrets
import os
import re
from datetime import date, datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DB_DIR = APP_DIR / "base_dados"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "hospital.db"

# Paleta visual
NAVY = "#17324D"
BLUE = "#246B9E"
LIGHT = "#F3F6FA"
WHITE = "#FFFFFF"
TEXT = "#263445"
MUTED = "#68788A"
GREEN = "#23845B"
RED = "#B43B3B"


def conectar():
    """Abre a base de dados e ativa a integridade referencial."""
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def hash_senha(senha, salt=None):
    """Gera hash PBKDF2; nunca guarda a palavra-passe em texto simples."""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, 200_000)
    return salt.hex() + ":" + digest.hex()


def verificar_senha(senha, valor_guardado):
    try:
        salt_hex, digest_hex = valor_guardado.split(":")
        salt = bytes.fromhex(salt_hex)
        calculado = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, 200_000)
        return secrets.compare_digest(calculado.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def criar_base_dados():
    with conectar() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS utilizadores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_utilizador TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            perfil TEXT NOT NULL CHECK(perfil IN ('Administrador','Profissional'))
        );

        CREATE TABLE IF NOT EXISTS utentes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numero_registo TEXT NOT NULL UNIQUE,
            nome TEXT NOT NULL,
            data_nascimento TEXT NOT NULL,
            sexo TEXT NOT NULL,
            telefone TEXT,
            nif TEXT UNIQUE,
            criado_em TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS consultas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            utente_id INTEGER NOT NULL,
            data_consulta TEXT NOT NULL,
            diagnostico TEXT NOT NULL,
            observacoes TEXT,
            profissional TEXT NOT NULL,
            criado_em TEXT NOT NULL,
            FOREIGN KEY (utente_id) REFERENCES utentes(id) ON DELETE RESTRICT
        );

        CREATE TABLE IF NOT EXISTS auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            utilizador TEXT NOT NULL,
            acao TEXT NOT NULL,
            detalhe TEXT NOT NULL,
            data_hora TEXT NOT NULL
        );
        """)
        existe = con.execute(
            "SELECT id FROM utilizadores WHERE nome_utilizador = ?", ("admin",)
        ).fetchone()
        if not existe:
            con.execute(
                "INSERT INTO utilizadores(nome_utilizador, senha_hash, perfil) VALUES(?,?,?)",
                ("admin", hash_senha("Admin@123"), "Administrador")
            )


def registar_auditoria(utilizador, acao, detalhe):
    with conectar() as con:
        con.execute(
            "INSERT INTO auditoria(utilizador,acao,detalhe,data_hora) VALUES(?,?,?,?)",
            (utilizador, acao, detalhe, datetime.now().isoformat(timespec="seconds"))
        )


def validar_data(valor):
    try:
        d = datetime.strptime(valor, "%Y-%m-%d").date()
        return d <= date.today()
    except ValueError:
        return False


def proximo_numero_registo():
    """Gera identificador legível e verifica a unicidade na base de dados."""
    while True:
        numero = "UT-" + datetime.now().strftime("%Y%m%d") + "-" + secrets.token_hex(3).upper()
        with conectar() as con:
            existe = con.execute(
                "SELECT 1 FROM utentes WHERE numero_registo = ?", (numero,)
            ).fetchone()
        if not existe:
            return numero


class SistemaUtentes:
    def __init__(self, root):
        self.root = root
        self.root.title("SREU | Sistema de Registo Eletrónico de Utentes")
        self.root.geometry("1120x720")
        self.root.minsize(980, 620)
        self.root.configure(bg=LIGHT)
        self.utilizador = None
        self.perfil = None
        self.estilizar()
        self.mostrar_login()

    def estilizar(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", rowheight=29, font=("Segoe UI", 10),
                        background=WHITE, fieldbackground=WHITE, foreground=TEXT)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"),
                        background="#E5ECF3", foreground=NAVY)
        style.map("Treeview", background=[("selected", "#D5E8F7")],
                  foreground=[("selected", TEXT)])
        style.configure("TCombobox", padding=6)
        style.configure("TEntry", padding=7)

    def limpar(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def titulo(self, parent, texto, subtitulo=None):
        tk.Label(parent, text=texto, bg=LIGHT, fg=NAVY,
                 font=("Segoe UI", 21, "bold")).pack(anchor="w", pady=(0, 4))
        if subtitulo:
            tk.Label(parent, text=subtitulo, bg=LIGHT, fg=MUTED,
                     font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 18))

    def botao(self, parent, texto, comando, cor=BLUE):
        return tk.Button(parent, text=texto, command=comando, bg=cor, fg=WHITE,
                         activebackground=NAVY, activeforeground=WHITE,
                         relief="flat", bd=0, padx=15, pady=9,
                         font=("Segoe UI", 10, "bold"), cursor="hand2")

    def mostrar_login(self):
        self.limpar()
        fundo = tk.Frame(self.root, bg=LIGHT)
        fundo.pack(fill="both", expand=True)
        cartao = tk.Frame(fundo, bg=WHITE, padx=42, pady=38,
                          highlightbackground="#DCE4EC", highlightthickness=1)
        cartao.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(cartao, text="SREU", bg=WHITE, fg=BLUE,
                 font=("Segoe UI", 30, "bold")).pack()
        tk.Label(cartao, text="Sistema de Registo Eletrónico de Utentes",
                 bg=WHITE, fg=NAVY, font=("Segoe UI", 12, "bold")).pack(pady=(0, 24))
        tk.Label(cartao, text="Nome de utilizador", bg=WHITE, fg=TEXT).pack(anchor="w")
        self.login_user = ttk.Entry(cartao, width=35)
        self.login_user.pack(pady=(5, 14))
        tk.Label(cartao, text="Palavra-passe", bg=WHITE, fg=TEXT).pack(anchor="w")
        self.login_pass = ttk.Entry(cartao, width=35, show="•")
        self.login_pass.pack(pady=(5, 20))
        self.botao(cartao, "ENTRAR", self.autenticar).pack(fill="x")
        tk.Label(cartao, text="Acesso demonstrativo inicial: admin / Admin@123",
                 bg=WHITE, fg=MUTED, font=("Segoe UI", 8)).pack(pady=(16, 0))
        self.login_pass.bind("<Return>", lambda event: self.autenticar())
        self.login_user.focus_set()

    def autenticar(self):
        nome = self.login_user.get().strip()
        senha = self.login_pass.get()
        with conectar() as con:
            user = con.execute(
                "SELECT * FROM utilizadores WHERE nome_utilizador = ?", (nome,)
            ).fetchone()
        if user and verificar_senha(senha, user["senha_hash"]):
            self.utilizador = user["nome_utilizador"]
            self.perfil = user["perfil"]
            registar_auditoria(self.utilizador, "LOGIN", "Autenticação bem-sucedida")
            self.mostrar_principal()
        else:
            messagebox.showerror("Acesso recusado", "Utilizador ou palavra-passe incorretos.")

    def mostrar_principal(self):
        self.limpar()
        topo = tk.Frame(self.root, bg=NAVY, height=66)
        topo.pack(fill="x")
        topo.pack_propagate(False)
        tk.Label(topo, text="SREU  |  Gestão de Utentes", bg=NAVY, fg=WHITE,
                 font=("Segoe UI", 17, "bold")).pack(side="left", padx=24, pady=15)
        tk.Label(topo, text=f"{self.utilizador}  •  {self.perfil}", bg=NAVY, fg=WHITE,
                 font=("Segoe UI", 10)).pack(side="right", padx=24)
        corpo = tk.Frame(self.root, bg=LIGHT)
        corpo.pack(fill="both", expand=True)
        nav = tk.Frame(corpo, bg="#203F5C", width=220)
        nav.pack(side="left", fill="y")
        nav.pack_propagate(False)
        tk.Label(nav, text="MENU PRINCIPAL", bg="#203F5C", fg="#C9D8E5",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=18, pady=(25, 12))
        itens = [
            ("Painel inicial", self.painel),
            ("Registar utente", self.formulario_utente),
            ("Pesquisar / consultar", self.pesquisar_utente),
            ("Registar consulta", self.formulario_consulta),
            ("Histórico clínico", self.historico),
        ]
        for texto, funcao in itens:
            tk.Button(nav, text=texto, command=funcao, anchor="w",
                      bg="#203F5C", fg=WHITE, activebackground=BLUE,
                      activeforeground=WHITE, relief="flat", padx=18, pady=13,
                      font=("Segoe UI", 10), cursor="hand2").pack(fill="x")
        if self.perfil == "Administrador":
            tk.Button(nav, text="Criar utilizador", command=self.criar_utilizador,
                      anchor="w", bg="#203F5C", fg=WHITE, activebackground=BLUE,
                      activeforeground=WHITE, relief="flat", padx=18, pady=13,
                      font=("Segoe UI", 10), cursor="hand2").pack(fill="x")
        tk.Button(nav, text="Terminar sessão", command=self.sair,
                  anchor="w", bg="#7D3030", fg=WHITE, relief="flat",
                  padx=18, pady=13, font=("Segoe UI", 10)).pack(side="bottom", fill="x")
        self.area = tk.Frame(corpo, bg=LIGHT, padx=28, pady=25)
        self.area.pack(side="left", fill="both", expand=True)
        self.painel()

    def limpar_area(self):
        for w in self.area.winfo_children():
            w.destroy()

    def painel(self):
        self.limpar_area()
        self.titulo(self.area, "Painel de controlo",
                    "Visão geral do Sistema de Registo Eletrónico de Utentes.")
        with conectar() as con:
            total = con.execute("SELECT COUNT(*) n FROM utentes").fetchone()["n"]
            consultas = con.execute("SELECT COUNT(*) n FROM consultas").fetchone()["n"]
            hoje = con.execute("SELECT COUNT(*) n FROM consultas WHERE date(data_consulta)=date('now','localtime')").fetchone()["n"]
        cards = tk.Frame(self.area, bg=LIGHT)
        cards.pack(fill="x", pady=12)
        for rotulo, numero, cor in [
            ("Utentes registados", total, BLUE),
            ("Consultas registadas", consultas, GREEN),
            ("Atendimentos de hoje", hoje, "#8A6B27")
        ]:
            card = tk.Frame(cards, bg=WHITE, padx=22, pady=20,
                            highlightbackground="#E0E6ED", highlightthickness=1)
            card.pack(side="left", fill="x", expand=True, padx=(0, 12))
            tk.Label(card, text=rotulo, bg=WHITE, fg=MUTED,
                     font=("Segoe UI", 10)).pack(anchor="w")
            tk.Label(card, text=str(numero), bg=WHITE, fg=cor,
                     font=("Segoe UI", 27, "bold")).pack(anchor="w", pady=(7, 0))
        aviso = tk.Label(self.area,
            text="Privacidade: consulte apenas os dados necessários às suas funções. "
                 "Use exclusivamente dados fictícios nesta demonstração.",
            bg="#FFF5DF", fg="#72551A", padx=15, pady=13, wraplength=760, justify="left")
        aviso.pack(fill="x", pady=22)

    def formulario_utente(self):
        self.limpar_area()
        self.titulo(self.area, "Registar novo utente",
                    "Preencha os dados pessoais. O número de registo será gerado automaticamente.")
        form = tk.Frame(self.area, bg=WHITE, padx=24, pady=22,
                        highlightbackground="#E0E6ED", highlightthickness=1)
        form.pack(fill="x", anchor="n")
        campos = {}
        definicoes = [
            ("Nome completo *", "nome"),
            ("Data de nascimento (AAAA-MM-DD) *", "nascimento"),
            ("Telefone", "telefone"),
            ("NIF (opcional)", "nif")
        ]
        for i, (rotulo, chave) in enumerate(definicoes):
            r, c = divmod(i, 2)
            tk.Label(form, text=rotulo, bg=WHITE, fg=TEXT).grid(
                row=r*2, column=c, sticky="w", padx=10, pady=(5, 3))
            entrada = ttk.Entry(form, width=38)
            entrada.grid(row=r*2+1, column=c, sticky="ew", padx=10, pady=(0, 12))
            campos[chave] = entrada
        tk.Label(form, text="Sexo", bg=WHITE, fg=TEXT).grid(
            row=4, column=0, sticky="w", padx=10, pady=(5, 3))
        sexo = ttk.Combobox(form, values=["Feminino", "Masculino", "Não especificado"],
                            state="readonly", width=35)
        sexo.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 12))
        sexo.set("Não especificado")
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        def guardar():
            nome = campos["nome"].get().strip()
            nasc = campos["nascimento"].get().strip()
            telefone = campos["telefone"].get().strip()
            nif = campos["nif"].get().strip() or None
            if len(nome) < 3:
                messagebox.showwarning("Validação", "Informe um nome válido.")
                return
            if not validar_data(nasc):
                messagebox.showwarning("Validação", "Data inválida. Use AAAA-MM-DD e não indique uma data futura.")
                return
            if telefone and not re.fullmatch(r"[0-9+() -]{6,20}", telefone):
                messagebox.showwarning("Validação", "Formato de telefone inválido.")
                return
            numero = proximo_numero_registo()
            try:
                with conectar() as con:
                    con.execute("""INSERT INTO utentes
                        (numero_registo,nome,data_nascimento,sexo,telefone,nif,criado_em)
                        VALUES(?,?,?,?,?,?,?)""",
                        (numero, nome, nasc, sexo.get(), telefone, nif,
                         datetime.now().isoformat(timespec="seconds")))
                registar_auditoria(self.utilizador, "REGISTO_UTENTE", numero)
                messagebox.showinfo("Sucesso", f"Utente registado!\nNúmero: {numero}")
                self.pesquisar_utente(numero)
            except sqlite3.IntegrityError:
                messagebox.showerror("Erro", "NIF já registado ou dados duplicados.")
        self.botao(self.area, "Guardar utente", guardar, GREEN).pack(anchor="w", pady=16)

    def pesquisar_utente(self, numero_inicial=""):
        self.limpar_area()
        self.titulo(self.area, "Pesquisar e consultar utentes",
                    "Pesquise pelo número de registo ou pelo nome.")
        barra = tk.Frame(self.area, bg=LIGHT)
        barra.pack(fill="x", pady=(0, 12))
        entrada = ttk.Entry(barra, width=42)
        entrada.pack(side="left", padx=(0, 10), ipady=5)
        entrada.insert(0, numero_inicial)
        tabela = self.criar_tabela(self.area,
            ("numero_registo", "nome", "nascimento", "sexo", "telefone"),
            ("N.º de registo", "Nome", "Nascimento", "Sexo", "Telefone"))
        tabela.pack(fill="both", expand=True)

        def procurar():
            termo = entrada.get().strip()
            for item in tabela.tree.get_children():
                tabela.tree.delete(item)
            with conectar() as con:
                rows = con.execute("""SELECT numero_registo,nome,data_nascimento,sexo,telefone
                    FROM utentes WHERE numero_registo LIKE ? OR nome LIKE ?
                    ORDER BY nome LIMIT 200""", (f"%{termo}%", f"%{termo}%")).fetchall()
            for row in rows:
                tabela.tree.insert("", "end", values=tuple(row))
            if not rows:
                messagebox.showinfo("Pesquisa", "Nenhum utente encontrado.")
            registar_auditoria(self.utilizador, "PESQUISA_UTENTE", termo or "consulta geral")

        self.botao(barra, "Pesquisar", procurar).pack(side="left")
        self.botao(barra, "Ver histórico do selecionado",
                   lambda: self.abrir_historico_selecionado(tabela), GREEN).pack(side="left", padx=8)
        procurar()

    def criar_tabela(self, parent, colunas, titulos):
        frame = tk.Frame(parent, bg=WHITE)
        tree = ttk.Treeview(frame, columns=colunas, show="headings", selectmode="browse")
        for col, titulo in zip(colunas, titulos):
            tree.heading(col, text=titulo)
            tree.column(col, width=150, anchor="w")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        # O frame é devolvido para permitir a disposição do conjunto.
        return frame_with_tree(frame, tree)

    def abrir_historico_selecionado(self, tabela):
        selecionado = tabela.tree.selection()
        if not selecionado:
            messagebox.showwarning("Seleção", "Selecione um utente na tabela.")
            return
        numero = tabela.tree.item(selecionado[0], "values")[0]
        self.historico(numero)

    def formulario_consulta(self):
        self.limpar_area()
        self.titulo(self.area, "Registar consulta",
                    "Associe o atendimento a um utente já registado.")
        form = tk.Frame(self.area, bg=WHITE, padx=24, pady=22,
                        highlightbackground="#E0E6ED", highlightthickness=1)
        form.pack(fill="x", anchor="n")
        labels = [
            ("Número de registo do utente *", "numero"),
            ("Data da consulta (AAAA-MM-DD) *", "data"),
            ("Diagnóstico *", "diagnostico"),
            ("Observações", "observacoes")
        ]
        entradas = {}
        for i, (rotulo, chave) in enumerate(labels):
            tk.Label(form, text=rotulo, bg=WHITE, fg=TEXT).grid(
                row=i*2, column=0, sticky="w", pady=(6, 3))
            if chave in ("diagnostico", "observacoes"):
                widget = tk.Text(form, width=75, height=3, font=("Segoe UI", 10))
            else:
                widget = ttk.Entry(form, width=55)
            widget.grid(row=i*2+1, column=0, sticky="ew", pady=(0, 10))
            entradas[chave] = widget
        entradas["data"].insert(0, date.today().isoformat())

        def valor(chave):
            w = entradas[chave]
            return w.get("1.0", "end").strip() if isinstance(w, tk.Text) else w.get().strip()

        def guardar():
            numero = valor("numero")
            data_consulta = valor("data")
            diagnostico = valor("diagnostico")
            observacoes = valor("observacoes")
            if not numero or not diagnostico or not validar_data(data_consulta):
                messagebox.showwarning("Validação", "Informe o utente, diagnóstico e uma data válida.")
                return
            with conectar() as con:
                utente = con.execute(
                    "SELECT id FROM utentes WHERE numero_registo = ?", (numero,)
                ).fetchone()
                if not utente:
                    messagebox.showerror("Utente inexistente", "Registe ou localize primeiro o utente.")
                    return
                con.execute("""INSERT INTO consultas
                    (utente_id,data_consulta,diagnostico,observacoes,profissional,criado_em)
                    VALUES(?,?,?,?,?,?)""",
                    (utente["id"], data_consulta, diagnostico, observacoes,
                     self.utilizador, datetime.now().isoformat(timespec="seconds")))
            registar_auditoria(self.utilizador, "REGISTO_CONSULTA", numero)
            messagebox.showinfo("Sucesso", "Consulta registada com sucesso.")
            self.historico(numero)
        self.botao(self.area, "Guardar consulta", guardar, GREEN).pack(anchor="w", pady=16)

    def historico(self, numero_inicial=""):
        self.limpar_area()
        self.titulo(self.area, "Histórico clínico",
                    "Acesso restrito a utilizadores autenticados e autorizados.")
        barra = tk.Frame(self.area, bg=LIGHT)
        barra.pack(fill="x", pady=(0, 12))
        entrada = ttk.Entry(barra, width=35)
        entrada.pack(side="left", padx=(0, 10), ipady=5)
        entrada.insert(0, numero_inicial)
        info = tk.Label(self.area, text="", bg=LIGHT, fg=NAVY,
                        font=("Segoe UI", 11, "bold"), justify="left")
        info.pack(anchor="w", pady=8)
        frame = self.criar_tabela(self.area,
            ("data", "diagnostico", "observacoes", "profissional"),
            ("Data", "Diagnóstico", "Observações", "Profissional"))
        frame.pack(fill="both", expand=True)

        def carregar():
            numero = entrada.get().strip()
            for item in frame.tree.get_children():
                frame.tree.delete(item)
            with conectar() as con:
                utente = con.execute(
                    "SELECT * FROM utentes WHERE numero_registo = ?", (numero,)
                ).fetchone()
                if not utente:
                    info.config(text="Utente não encontrado.")
                    return
                rows = con.execute("""SELECT data_consulta,diagnostico,observacoes,profissional
                    FROM consultas WHERE utente_id = ? ORDER BY data_consulta DESC""",
                    (utente["id"],)).fetchall()
            info.config(text=f"Utente: {utente['nome']}    |    Registo: {utente['numero_registo']}")
            for row in rows:
                frame.tree.insert("", "end", values=tuple(row))
            registar_auditoria(self.utilizador, "CONSULTA_HISTORICO", numero)

        self.botao(barra, "Carregar histórico", carregar).pack(side="left")
        if numero_inicial:
            carregar()

    def criar_utilizador(self):
        if self.perfil != "Administrador":
            messagebox.showerror("Acesso negado", "Apenas o administrador pode criar utilizadores.")
            return
        self.limpar_area()
        self.titulo(self.area, "Criar utilizador",
                    "Crie contas individuais; não partilhe palavras-passe.")
        form = tk.Frame(self.area, bg=WHITE, padx=24, pady=22)
        form.pack(fill="x")
        tk.Label(form, text="Nome de utilizador", bg=WHITE).pack(anchor="w")
        nome = ttk.Entry(form, width=40)
        nome.pack(anchor="w", pady=(3, 12))
        tk.Label(form, text="Palavra-passe (mínimo 10 caracteres)", bg=WHITE).pack(anchor="w")
        senha = ttk.Entry(form, width=40, show="•")
        senha.pack(anchor="w", pady=(3, 12))
        tk.Label(form, text="Perfil", bg=WHITE).pack(anchor="w")
        perfil = ttk.Combobox(form, values=["Profissional", "Administrador"],
                              state="readonly", width=37)
        perfil.set("Profissional")
        perfil.pack(anchor="w", pady=(3, 14))

        def guardar():
            n, s = nome.get().strip(), senha.get()
            if len(n) < 3 or len(s) < 10:
                messagebox.showwarning("Validação", "Nome com 3+ caracteres e senha com 10+ caracteres.")
                return
            try:
                with conectar() as con:
                    con.execute("INSERT INTO utilizadores(nome_utilizador,senha_hash,perfil) VALUES(?,?,?)",
                                (n, hash_senha(s), perfil.get()))
                registar_auditoria(self.utilizador, "CRIACAO_UTILIZADOR", n)
                messagebox.showinfo("Sucesso", "Utilizador criado.")
                self.painel()
            except sqlite3.IntegrityError:
                messagebox.showerror("Erro", "Esse nome de utilizador já existe.")
        self.botao(self.area, "Criar conta", guardar, GREEN).pack(anchor="w", pady=15)

    def sair(self):
        registar_auditoria(self.utilizador, "LOGOUT", "Sessão terminada")
        self.utilizador = None
        self.perfil = None
        self.mostrar_login()


class TabelaComFrame:
    """Contentor simples para expor o Treeview e o respetivo Frame."""
    def __init__(self, frame, tree):
        self.frame = frame
        self.tree = tree

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)


def frame_with_tree(frame, tree):
    return TabelaComFrame(frame, tree)


def iniciar():
    criar_base_dados()
    root = tk.Tk()
    SistemaUtentes(root)
    root.mainloop()


if __name__ == "__main__":
    iniciar()
