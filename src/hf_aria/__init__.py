def main():
    from hf_aria.cli import parse_args, handle_early_exit
    from hf_aria.resolver import resolve_batch
    from hf_aria.downloader import run_download

    args = parse_args()
    if handle_early_exit(args):
        return
    batch = resolve_batch(args)
    run_download(batch, args)
