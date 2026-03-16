"""generate_stubs.py -- CLI wrapper for stub generator. Delegates to stub_generator.main()."""
from stub_generator import main, write_stub_file, write_upstream_stubs


if __name__ == "__main__":
    main()
