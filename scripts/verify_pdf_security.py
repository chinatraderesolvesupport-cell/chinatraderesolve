from app.documents import pdf_security_self_test

if not pdf_security_self_test():
    raise SystemExit("PDF security self-test failed")
print("PDF security self-test passed")
