key = hash_file("AGENTS.md");
flag = xor_blob(encrypted_flag, key);
puts(flag);
recycle key;
