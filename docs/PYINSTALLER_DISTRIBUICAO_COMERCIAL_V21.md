# Boxio v1.21 — Empacotamento comercial com PyInstaller

## Comando básico

```powershell
pyinstaller --noconfirm --windowed --name Boxio main.py
```

## Recomendações

Para distribuição comercial:

- usar caminho curto no Windows, como `D:\BoxioBuild`;
- incluir assets;
- incluir `.env` modelo sem senhas;
- não empacotar código-fonte separado;
- assinar o executável futuramente;
- distribuir instalador ao invés de pasta solta;
- preservar dados em AppData;
- usar GitHub Releases para versões.

## Exemplo com assets

```powershell
pyinstaller --noconfirm --windowed --name Boxio ^
  --add-data "assets;assets" ^
  --add-data "config;config" ^
  main.py
```

## Proteção básica

- não enviar `.py` ao cliente;
- usar executável/instalador;
- manter validação online;
- limitar ativações por dispositivo;
- assinar instalador futuramente;
- usar licença anual com revogação no servidor;
- manter logs de ativação e update.

## Importante

PyInstaller não é criptografia. Ele dificulta acesso casual ao código, mas não impede engenharia reversa avançada. A proteção comercial real vem da combinação:

- licença online;
- servidor de ativação;
- controle de dispositivos;
- assinatura de instalador;
- atualizações contínuas;
- contrato comercial.
