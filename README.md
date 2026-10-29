# SuperOS / G-Auto

Sistema web para gestão básica de oficina mecânica, feito com Flask, Jinja, Bootstrap e Supabase.

## Requisitos

- Python 3.11 ou superior recomendado.
- Projeto Supabase com as tabelas usadas pelo sistema.
- Credenciais do Supabase configuradas no ambiente local.

## Instalação local

1. Extraia o ZIP e entre na pasta `projetofinal708-main`.
2. Crie e ative um ambiente virtual:

   **Windows (PowerShell):**
   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   **Linux/macOS:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Instale as dependências:
   ```bash
   python -m pip install -r requirements.txt
   ```
4. Copie `.env.example` para `.env` e preencha `SUPABASE_URL`, `SUPABASE_KEY` e `SECRET_KEY`.
   - Gere uma `SECRET_KEY` longa e exclusiva; não use o texto de exemplo.
   - Não envie o arquivo `.env` para repositórios nem compartilhe suas credenciais.
   - Em produção com HTTPS, defina `COOKIE_SECURE=true`.
5. Inicie o sistema:
   ```bash
   python app.py
   ```
6. Abra `http://127.0.0.1:5000` no navegador.

## Funcionalidades presentes

- Login de usuários existentes na tabela `usuarios`.
- Dashboard com totais e relatório de ordens de serviço.
- Cadastro e listagem de veículos, com edição e exclusão.
- Cadastro de clientes, funcionários e ordens de serviço.
- Listagem de clientes e funcionários ativos/inativos.
- Edição de clientes, funcionários, veículos e ordens de serviço.
- Inativação e reativação de clientes e funcionários.
- Exclusão de ordens de serviço.
- Layout responsivo com Bootstrap.

## Observações importantes

- O código espera que as tabelas `usuarios`, `clientes`, `funcionarios`, `veiculos` e `registro_os` existam no Supabase com os campos referenciados nas rotas e nos templates. Este pacote não inclui uma exportação do esquema nem dados do banco.
- As colunas `ativo` de clientes e funcionários precisam aceitar valores booleanos e ter os valores existentes corretamente preenchidos.
- O login mantém compatibilidade com senhas antigas em texto puro e tenta convertê-las para hash no primeiro login bem-sucedido. Para contas novas, grave senhas usando `werkzeug.security.generate_password_hash`; nunca armazene senhas em texto puro.
- As ações que alteram dados agora usam POST e token CSRF. Se criar novos formulários POST, inclua `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
- O módulo de estoque não foi implementado porque o pacote não inclui um esquema de banco para produtos/peças. O item de menu que não funcionava foi removido para evitar um link sem destino.
- A listagem de veículos consulta os dados da tabela `veiculos` e associa o nome do cliente usando `cliente_id`.

## Verificações realizadas nesta revisão

- Sintaxe Python validada com `py_compile`.
- Templates Jinja validados quanto à sintaxe.
- Referências `url_for(...)` comparadas às rotas existentes.

Não foi possível executar um teste de integração com o Supabase nesta revisão porque as credenciais e a estrutura real do banco não acompanham o ZIP. Faça os testes finais no ambiente configurado antes de publicar.
