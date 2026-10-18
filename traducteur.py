#!/usr/bin/env python3
"""Traducteur de bureau : Argos hors ligne et Google Cloud en ligne."""
import argparse
import html
import json
import os
from pathlib import Path
import queue
import threading
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parent
# Les modèles suivent le dossier de l'application pour pouvoir le copier hors ligne.
os.environ.setdefault('ARGOS_PACKAGES_DIR', str(ROOT / 'modeles'))
os.environ.setdefault('ARGOS_DEVICE_TYPE', 'cpu')


def argos():
    try:
        import argostranslate.package as package
        import argostranslate.translate as translate
        return package, translate
    except ImportError as exc:
        raise RuntimeError('Installez les dépendances : python -m pip install -r requirements.txt') from exc


def google_request(endpoint, key, payload=None):
    if not key.strip():
        raise RuntimeError('Saisissez votre clé Google Cloud Translation.')
    url = 'https://translation.googleapis.com/language/translate/v2' + endpoint
    data = json.dumps(payload).encode('utf-8') if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={
        'Content-Type': 'application/json; charset=utf-8', 'X-Goog-Api-Key': key.strip()})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.load(response)['data']
    except urllib.error.HTTPError as exc:
        # Ne jamais afficher l'URL ou la clé dans les erreurs.
        raise RuntimeError(f'Google refuse la requête (HTTP {exc.code}). Vérifiez clé, API activée, quotas et facturation.') from None
    except urllib.error.URLError:
        raise RuntimeError('Connexion Google impossible. Vérifiez votre accès Internet.') from None


def offline_translate(text, source, target):
    _, translate = argos()
    languages = {lang.code: lang for lang in translate.get_installed_languages()}
    if source not in languages or target not in languages:
        raise RuntimeError('Modèles manquants : ouvrez « Langues hors ligne ».')
    try:
        translator = languages[source].get_translation(languages[target])
    except Exception:
        raise RuntimeError('Aucun parcours installé pour cette paire. Installez les modèles correspondants, éventuellement via anglais.') from None
    if translator is None:
        raise RuntimeError('Aucun modèle installé pour cette paire.')
    return translator.translate(text)


def install_models(packages, progress, cancelled):
    package, _ = argos()
    installed = {(p.from_code, p.to_code, str(p.package_version)) for p in package.get_installed_packages()}
    failures = []
    for i, item in enumerate(packages, 1):
        if cancelled.is_set():
            return 'Téléchargement arrêté après le modèle courant.'
        identity = (item.from_code, item.to_code, str(item.package_version))
        if identity in installed:
            continue
        progress(f'{i}/{len(packages)} : {item.from_name} → {item.to_name}')
        try:
            path = item.download()
            package.install_from_path(path)
            installed.add(identity)
        except Exception:
            failures.append(f'{item.from_code} → {item.to_code}')
    if failures:
        return 'Terminé avec échecs (relancez pour réessayer) : ' + ', '.join(failures)
    return 'Tous les modèles demandés sont installés. Le mode hors ligne est prêt.'


def main():
    import tkinter as tk
    from tkinter import ttk, messagebox
    root = tk.Tk()
    root.title('Traducteur — local et Google')
    root.geometry('1100x720')
    root.minsize(780, 570)
    root.configure(bg='#f8fafd')
    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('TFrame', background='#f8fafd')
    style.configure('TLabel', background='#f8fafd', font=('DejaVu Sans', 11))
    style.configure('TButton', padding=9)
    events = queue.Queue()
    busy = False
    models = []
    cancelled = threading.Event()
    names = {'fr': 'Français', 'en': 'Anglais', 'es': 'Espagnol', 'de': 'Allemand', 'it': 'Italien', 'pt': 'Portugais', 'ar': 'Arabe', 'zh': 'Chinois', 'ja': 'Japonais', 'ru': 'Russe', 'bg': 'Bulgare'}
    labels = {}
    mode = tk.StringVar(value='Hors ligne')
    status = tk.StringVar(value='Hors ligne : installez les modèles avant la première traduction.')
    key = tk.StringVar(value=os.environ.get('GOOGLE_TRANSLATE_API_KEY', ''))

    def refresh_languages(extra=None):
        if extra:
            names.update(extra)
        try:
            package, _ = argos()
            for p in package.get_installed_packages():
                names.setdefault(p.from_code, p.from_name)
                names.setdefault(p.to_code, p.to_name)
        except RuntimeError:
            pass
        labels.clear()
        labels.update({f'{name} [{code}]': code for code, name in sorted(names.items(), key=lambda x: x[1])})
        for box in (source, target):
            old = box.get()
            box['values'] = list(labels)
            if old in labels:
                box.set(old)
        if not source.get():
            source.set('Français [fr]')
        if not target.get():
            target.set('Anglais [en]')

    def run(job, done):
        nonlocal busy
        if busy:
            messagebox.showinfo('Opération en cours', 'Attendez la fin de l’opération actuelle.')
            return
        busy = True
        status.set('Traitement en cours…')
        def worker():
            try:
                result = job()
                events.put(lambda result=result: done(result))
            except Exception as exc:
                message = str(exc) or type(exc).__name__
                events.put(lambda message=message: status.set('Erreur : ' + message))
            finally:
                events.put(finish)
        threading.Thread(target=worker, daemon=True).start()

    def finish():
        nonlocal busy
        busy = False

    def poll():
        try:
            while True:
                events.get_nowait()()
        except queue.Empty:
            pass
        root.after(100, poll)

    def translate_now():
        text = input_text.get('1.0', 'end-1c').strip()
        if not text:
            status.set('Saisissez un texte à traduire.')
            return
        if len(text) > 5000:
            status.set('Limite : 5 000 caractères par traduction. Divisez votre texte.')
            return
        src, dst = labels[source.get()], labels[target.get()]
        selected_mode, api_key = mode.get(), key.get()
        def job():
            if src == dst:
                return text
            if selected_mode == 'Google en ligne':
                response = google_request('', api_key, {'q': text, 'source': src, 'target': dst, 'format': 'text'})
                return html.unescape(response['translations'][0]['translatedText'])
            return offline_translate(text, src, dst)
        def done(result):
            output_text.configure(state='normal')
            output_text.delete('1.0', 'end')
            output_text.insert('1.0', result)
            output_text.configure(state='disabled')
            status.set('Traduction terminée — ' + selected_mode)
        run(job, done)

    def manager():
        window = tk.Toplevel(root)
        window.title('Langues hors ligne')
        window.geometry('650x470')
        ttk.Label(window, text='1. Actualisez le catalogue. 2. Sélectionnez les modèles.').pack(pady=10)
        ttk.Label(window, text='Tous les modèles peuvent occuper plusieurs Go. Internet requis pour les installer.').pack()
        listing = tk.Listbox(window, selectmode='extended', exportselection=False)
        listing.pack(fill='both', expand=True, padx=15, pady=12)
        scrollbar = ttk.Scrollbar(listing, command=listing.yview)
        scrollbar.pack(side='right', fill='y')
        listing.configure(yscrollcommand=scrollbar.set)
        def catalogue():
            def job():
                package, _ = argos()
                package.update_package_index()
                return [p for p in package.get_available_packages() if getattr(p, 'type', 'translate') == 'translate']
            def done(result):
                nonlocal models
                models = result
                if not window.winfo_exists():
                    return
                listing.delete(0, 'end')
                extra = {}
                for p in models:
                    listing.insert('end', f'{p.from_name} [{p.from_code}] → {p.to_name} [{p.to_code}]')
                    extra.update({p.from_code: names.get(p.from_code, p.from_name), p.to_code: names.get(p.to_code, p.to_name)})
                refresh_languages(extra)
                status.set(f'{len(models)} modèles disponibles dans le catalogue.')
            run(job, done)
        def install(all_models=False):
            if not models:
                status.set('Actualisez d’abord le catalogue.')
                return
            chosen = list(models) if all_models else [models[i] for i in listing.curselection()]
            if not chosen:
                return
            cancelled.clear()
            def progress(message):
                events.put(lambda message=message: status.set(message))
            def done(message):
                refresh_languages()
                status.set(message)
            run(lambda: install_models(chosen, progress, cancelled), done)
        buttons = ttk.Frame(window)
        buttons.pack(pady=8)
        ttk.Button(buttons, text='Actualiser', command=catalogue).pack(side='left')
        ttk.Button(buttons, text='Installer la sélection', command=install).pack(side='left', padx=6)
        ttk.Button(buttons, text='Tout installer', command=lambda: install(True)).pack(side='left')
        ttk.Button(window, text='Arrêter après le modèle courant', command=cancelled.set).pack(pady=8)

    header = ttk.Frame(root, padding=22)
    header.pack(fill='x')
    ttk.Label(header, text='Traduction', font=('DejaVu Sans', 25, 'bold'), foreground='#1967d2').pack(side='left')
    ttk.Button(header, text='Langues hors ligne', command=manager).pack(side='right')
    settings = ttk.Frame(root, padding=(22, 0, 22, 12))
    settings.pack(fill='x')
    ttk.Combobox(settings, textvariable=mode, values=['Hors ligne', 'Google en ligne'], state='readonly', width=18).pack(side='left')
    ttk.Label(settings, text='  Clé Google : ').pack(side='left')
    ttk.Entry(settings, textvariable=key, show='•', width=32).pack(side='left')
    def load_google():
        api_key = key.get()
        def done(data):
            refresh_languages({item['language']: item.get('name', item['language']) for item in data['languages']})
            status.set('Liste Google actualisée. Choisissez Google en ligne pour ces langues.')
        run(lambda: google_request('/languages?target=fr', api_key), done)
    ttk.Button(settings, text='Langues Google', command=load_google).pack(side='right')
    selectors = ttk.Frame(root, padding=(22, 4))
    selectors.pack(fill='x')
    source = ttk.Combobox(selectors, state='readonly', width=30)
    source.pack(side='left')
    def swap():
        a, b = source.get(), target.get()
        source.set(b)
        target.set(a)
    ttk.Button(selectors, text='⇄', command=swap).pack(side='left', padx=18)
    target = ttk.Combobox(selectors, state='readonly', width=30)
    target.pack(side='left')
    panes = ttk.Panedwindow(root, orient='horizontal')
    panes.pack(fill='both', expand=True, padx=22, pady=12)
    for title, editable in [('Texte à traduire', True), ('Traduction', False)]:
        frame = ttk.Frame(panes, padding=10)
        ttk.Label(frame, text=title).pack(anchor='w', pady=6)
        text_widget = tk.Text(frame, wrap='word', font=('DejaVu Sans', 15), relief='flat', padx=12, pady=12, undo=editable, width=35)
        text_widget.pack(fill='both', expand=True)
        if editable:
            input_text = text_widget
        else:
            output_text = text_widget
            output_text.configure(state='disabled')
        panes.add(frame, weight=1)
    actions = ttk.Frame(root, padding=(22, 0))
    actions.pack(fill='x')
    ttk.Button(actions, text='Traduire  (Ctrl+Entrée)', command=translate_now).pack(side='left')
    def copy():
        root.clipboard_clear()
        root.clipboard_append(output_text.get('1.0', 'end-1c'))
    ttk.Button(actions, text='Copier la traduction', command=copy).pack(side='right')
    ttk.Label(root, textvariable=status, wraplength=1000, padding=20).pack(fill='x')
    root.bind('<Control-Return>', lambda event: translate_now())
    refresh_languages()
    poll()
    root.mainloop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--installer-tout', action='store_true', help='Télécharger tous les modèles Argos disponibles sans interface')
    args = parser.parse_args()
    if args.installer_tout:
        pkg, _ = argos()
        pkg.update_package_index()
        available = [p for p in pkg.get_available_packages() if getattr(p, 'type', 'translate') == 'translate']
        print(install_models(available, print, threading.Event()))
    else:
        main()
