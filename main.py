#!/usr/bin/env python3
"""Abliteration Suite - CLI for Unrestricted LLM API Harvesting & Testing."""

import sys
import os
import asyncio
import argparse
import logging
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
import rich.box as box

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from src.config import (
    BASE_URL,
    API_BASE_URL,
    SIGNUP_URL,
    FLAGSHIP_MODEL,
    MODELS,
    HEADLESS,
    KEYS_TXT,
    ACCOUNTS_JSON,
)
from src.accounts import load_keys, load_state, record_account, update_status, save_key_to_file
from src.client import AbliterationClient
from src.outlook_graph import get_oauth_account
from src.browser import (
    solve_turnstile,
    start_signup_flow,
    submit_otp_code,
    harvest_api_key_from_console,
)
from camoufox.async_api import AsyncCamoufox

console = Console()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def print_banner():
    content = Text.assemble(
        Text("ABLITERATION AUTOMATION SUITE", style="bold red"), "\n",
        Text("Uncensored GLM-5.3 & Large Model Harvester • WorkOS Bypass • Key Pool", style="dim"), "\n\n",
        Text(f"Portal Endpoint : {BASE_URL}", style="cyan"), "\n",
        Text(f"API Base URL    : {API_BASE_URL}/v1", style="cyan"), "\n",
        Text(f"Flagship Model  : {FLAGSHIP_MODEL} (GLM-5.3 Unrestricted)", style="yellow"), "\n",
        Text(f"Key Storage     : {KEYS_TXT}", style="bright_black"),
    )
    console.print(Panel(content, box=box.ROUNDED, border_style="red"))


async def cmd_e2e(args):
    print_banner()
    query = args.account or "rian.nugroho"
    mb = get_oauth_account(query)
    if not mb:
        console.print(f"[bold red]Account matching '{query}' not found in /root/live_script/accounts_oauth.txt[/]")
        return

    email = mb.email
    password = args.password or "AbliterationRian2026!@#"
    console.print(f"[bold cyan]Running Fully Autonomous E2E Flow for: {email}[/]")
    console.print(f"[dim]Mailbox reader: Microsoft Graph API via OAuth refresh token[/]\n")

    initial_msgs = mb.poll_messages(limit=10)
    seen_ids = set(m.get("id") for m in initial_msgs if m.get("id"))
    console.print(f"[*] Indexed {len(seen_ids)} existing messages in Outlook mailbox.")

    async with AsyncCamoufox(headless=not args.headed) as browser:
        page = await browser.new_page()

        # Step 1: Submit signup form & solve Turnstile
        console.print(f"\n[1/4] Navigating & solving Turnstile for {email}...")
        signup_res = await start_signup_flow(page, email, password)
        if not signup_res.get("success"):
            console.print(f"[bold red]✗ Signup failed: {signup_res.get('error')}[/]")
            return
        console.print(f"[bold green]✓ Registration accepted by WorkOS! Waiting for 6-digit OTP...[/]")

        # Step 2: Poll Microsoft Graph API for fresh OTP
        console.print(f"\n[2/4] Polling Microsoft Graph API for fresh verification email...")
        otp = mb.wait_for_otp(timeout=65, ignore_ids=seen_ids)
        if not otp:
            console.print("[bold red]✗ Timeout: OTP did not arrive in Outlook.[/]")
            return

        console.print(f"[bold green]🎉 RECEIVED FRESH OTP:[/] [bold yellow]{otp}[/]! Submitting to verification form...")

        # Step 3: Submit OTP
        console.print(f"\n[3/4] Submitting OTP {otp} to Abliteration verification screen...")
        verify_res = await submit_otp_code(page, otp)
        if not verify_res.get("success"):
            console.print(f"[bold red]✗ Verification failed: {verify_res.get('error')}[/]")
            return
        console.print(f"[bold green]✓ Verification SUCCESS! Logged in & landed on: {verify_res.get('url')}[/]")
        await asyncio.sleep(4)

        # Step 4: Extract API key & test inference
        console.print(f"\n[4/4] Minting & harvesting API key from console...")
        key_res = await harvest_api_key_from_console(page)
        api_key = key_res.get("api_key")

        if api_key:
            console.print(f"[bold green]🎉 HARVESTED API KEY:[/] [bold yellow]{api_key}[/]")
            record_account(email, password, api_key=api_key, status="ACTIVE")

            console.print(f"\n[*] Testing live inference with {FLAGSHIP_MODEL} (GLM-5.3)...")
            client = AbliterationClient(api_key)
            test_res = client.check_key_validity()
            console.print(f"Inference response: {test_res}")
        else:
            console.print(f"[yellow]Auto-key extraction details: {key_res}[/]")
            record_account(email, password, status="VERIFIED_ACTIVE")


async def cmd_signup(args):
    print_banner()
    email = args.email
    password = args.password or "Abliteration2026!@#"

    if not email:
        console.print("[bold red]Error: --email wajib diisi.[/]")
        return

    console.print(f"[bold cyan]Memulai alur registrasi untuk: {email}...[/]\n")

    async with AsyncCamoufox(headless=not args.headed) as browser:
        page = await browser.new_page()

        # Step 1: Submit signup form & solve Turnstile
        console.print("[1/3] Step 1: Solving Turnstile dan mengirimkan formulir registrasi...")
        res = await start_signup_flow(page, email, password)

        if not res.get("success"):
            console.print(f"[bold red]✗ Step 1 Gagal: {res.get('error')}[/]")
            return

        record_account(email, password, status="PENDING_OTP")
        console.print("[bold green]✓ Step 1 Sukses! Kode verifikasi telah dikirim ke email kamu.[/]\n")

        # Step 2: Input OTP
        code = args.code
        if not code:
            console.print(f"[bold yellow][2/3] Step 2: Cek kotak masuk email {email} untuk 6-digit kode OTP.[/]")
            code = console.input(f"[bold cyan]>> Masukkan kode OTP 6-digit: [/]").strip()

        if not code or len(code) != 6:
            console.print("[bold red]Kode OTP tidak valid (harus 6 digit).[/]")
            return

        # Step 3: Submit OTP
        console.print(f"\n[3/3] Step 3: Memverifikasi kode OTP {code} ke Abliteration...")
        otp_res = await submit_otp_code(page, code)

        if not otp_res.get("success"):
            console.print(f"[bold red]✗ Verifikasi OTP gagal: {otp_res.get('error')}[/]")
            return

        console.print("[bold green]✓ Akun berhasil diverifikasi dan aktif![/]")

        # Step 4: Harvest API Key
        console.print("[cyan]Membuka /console/api-keys untuk mengambil API Key...[/]")
        key_res = await harvest_api_key_from_console(page)

        api_key = key_res.get("api_key")
        if api_key:
            update_status(email, status="ACTIVE", api_key=api_key)
            console.print(f"[bold green]🎉 API Key Berhasil Dipanen:[/] [bold yellow]{api_key}[/]\n")

            # Quick test inference
            console.print(f"[cyan]Testing key dengan {FLAGSHIP_MODEL}...[/]")
            client = AbliterationClient(api_key)
            test_res = client.check_key_validity()
            if test_res.get("valid"):
                console.print(f"[bold green]✓ Test Inference Sukses:[/] {test_res.get('answer')}")
            else:
                console.print(f"[yellow]Test response:[/] {test_res}")
        else:
            update_status(email, status="ACTIVE_NO_KEY")
            console.print(f"[yellow]Akun aktif, namun API key perlu digenerate manual dari dashboard console.[/]")


def cmd_chat(args):
    print_banner()
    keys = load_keys()
    if not keys:
        console.print("[bold red]Belum ada API key tersimpan. Tambahkan dengan `add-key` dahulu.[/]")
        return

    key = keys[0]
    model = args.model or FLAGSHIP_MODEL
    prompt = args.prompt or "Halo! Jelaskan secara singkat apa keunggulan model abliterated tanpa refusal filter."

    console.print(f"[cyan]Model:[/] [bold green]{model}[/] | [cyan]Prompt:[/] {prompt}")
    console.print(f"[dim]Mengirim request ke {API_BASE_URL}/v1/chat/completions...[/]\n")

    client = AbliterationClient(key)
    res = client.chat_completion(
        messages=[{"role": "user", "content": prompt}],
        model=model
    )

    if "choices" in res:
        ans = res["choices"][0]["message"]["content"]
        console.print(f"[bold white]{ans.strip()}[/]\n")
    else:
        console.print(f"[bold red]Error:[/] {res}")


def cmd_models(args):
    print_banner()
    console.print("[bold cyan]Katalog Model Uncensored / Abliterated di Abliteration AI:[/]\n")

    table = Table(box=box.ROUNDED)
    table.add_column("No", justify="right", style="dim")
    table.add_column("Model ID", style="bold green")
    table.add_column("Context", justify="center")
    table.add_column("Modalities", justify="center")
    table.add_column("Deskripsi", style="white")

    specs = [
        ("abliterated-model-large-v2", "1M", "Text Only", "GLM-5.3 uncensored frontier reasoning (Flagship)"),
        ("abliterated-model-large", "1M", "Text Only", "Frontier-scale uncensored reasoning"),
        ("abliterated-model", "256K", "Text + Vision", "General-purpose uncensored text with image inputs"),
    ]

    for i, (m, ctx, mod, desc) in enumerate(specs, 1):
        table.add_row(str(i), m, ctx, mod, desc)

    console.print(table)


def cmd_add_key(args):
    print_banner()
    key = args.key.strip()
    if not key:
        console.print("[bold red]Error: Key tidak boleh kosong.[/]")
        return

    save_key_to_file(key)
    console.print(f"[bold green]✓ API Key tersimpan ke {KEYS_TXT}![/]")

    client = AbliterationClient(key)
    test = client.check_key_validity()
    if test.get("valid"):
        console.print(f"[bold green]✓ Key Valid![/] Respon: {test.get('answer')}")
    else:
        console.print(f"[yellow]Hasil validasi:[/] {test}")


def cmd_list(args):
    print_banner()
    keys = load_keys()
    state = load_state()

    console.print(f"[bold green]Total API Key Tersedia:[/] {len(keys)}\n")

    table = Table(title="Daftar Akun & Keys Abliteration", box=box.ROUNDED)
    table.add_column("No", justify="right", style="dim")
    table.add_column("Email", style="cyan")
    table.add_column("Status", justify="center")
    table.add_column("Key Preview", style="green")
    table.add_column("Last Updated", style="dim")

    for i, (email, data) in enumerate(state.items(), 1):
        k = data.get("api_key", "-")
        k_prev = f"{k[:10]}...{k[-6:]}" if len(k) > 16 else k
        table.add_row(
            str(i),
            email,
            data.get("status", "UNKNOWN"),
            k_prev,
            data.get("updated_at", "-")[:19]
        )

    console.print(table)


async def cmd_test_turnstile(args):
    print_banner()
    console.print("[cyan]Benchmarking Turnstile bypass di abliteration.ai...[/]")
    import time

    start = time.time()
    async with AsyncCamoufox(headless=True) as browser:
        page = await browser.new_page()
        await page.goto(SIGNUP_URL, wait_until="domcontentloaded")
        await asyncio.sleep(3)

        solved, token = await solve_turnstile(page)
        dur = time.time() - start
        if solved:
            console.print(f"[bold green]✓ Turnstile solved dalam {dur:.2f}s![/]")
            console.print(f"Token len: {len(token)} | Token: [bright_black]{token[:60]}...[/]")
        else:
            console.print("[bold red]✗ Turnstile benchmark failed.[/]")


def main():
    parser = argparse.ArgumentParser(description="Abliteration Automation Suite")
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")

    # e2e
    p_e2e = subparsers.add_parser("e2e", help="Fully autonomous registration, Graph OTP read, and key harvesting")
    p_e2e.add_argument("-a", "--account", default="rian.nugroho", help="Account query in accounts_oauth.txt (default: rian.nugroho)")
    p_e2e.add_argument("-p", "--password", help="Account password")
    p_e2e.add_argument("--headed", action="store_true", help="Display browser visually")

    # signup
    p_reg = subparsers.add_parser("signup", aliases=["reg"], help="Register account via email + Turnstile + OTP")
    p_reg.add_argument("--email", "-e", required=True, help="Target email address")
    p_reg.add_argument("--password", "-p", help="Password for account (min 12 chars)")
    p_reg.add_argument("--code", "-c", help="6-digit OTP code (if already known)")
    p_reg.add_argument("--headed", action="store_true", help="Display browser visually")

    # chat
    p_chat = subparsers.add_parser("chat", help="Run test inference using saved key")
    p_chat.add_argument("-m", "--model", default=FLAGSHIP_MODEL, help="Model ID")
    p_chat.add_argument("prompt", nargs="?", help="Chat prompt")

    # models
    subparsers.add_parser("models", help="List available uncensored models")

    # add-key
    p_add = subparsers.add_parser("add-key", help="Manually store an existing API key")
    p_add.add_argument("key", help="API key")

    # list
    subparsers.add_parser("list", aliases=["ls"], help="List stored accounts and keys")

    # test-turnstile
    subparsers.add_parser("test-turnstile", help="Benchmark Turnstile solver speed")

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    if args.subcommand == "e2e":
        asyncio.run(cmd_e2e(args))
    elif args.subcommand in ("signup", "reg"):
        asyncio.run(cmd_signup(args))
    elif args.subcommand == "chat":
        cmd_chat(args)
    elif args.subcommand == "models":
        cmd_models(args)
    elif args.subcommand == "add-key":
        cmd_add_key(args)
    elif args.subcommand in ("list", "ls"):
        cmd_list(args)
    elif args.subcommand == "test-turnstile":
        asyncio.run(cmd_test_turnstile(args))


if __name__ == "__main__":
    main()
