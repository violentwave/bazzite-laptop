---
language: rust
domain: security
type: pattern
title: Memory safety guarantees in Rust
tags: rust, memory-safety, ownership, borrow-checker, security
---

# Memory Safety Guarantees in Rust

Rust's ownership system prevents common memory safety vulnerabilities at compile time.

## Ownership Basics

```rust
// Each value has a single owner
let s1 = String::from("hello");
let s2 = s1; // s1 is moved to s2, s1 is no longer valid

// Function takes ownership
fn take_ownership(s: String) {
    println!("{}", s);
} // s is dropped here

let s = String::from("hello");
take_ownership(s);
// s is no longer valid here

// Borrowing instead
fn borrow(s: &String) -> usize {
    s.len()
}
let s = String::from("hello");
let len = borrow(&s); // s still valid
```

## Preventing Buffer Overflow

```rust
// Safe array access with bounds checking
let vec = vec![1, 2, 3];
match vec.get(10) {
    Some(value) => println!("Got: {}", value),
    None => println!("Index out of bounds"),
}

// Index operator panics on out-of-bounds (use get for safe)
let value = vec[1]; // panics if index invalid
```

## Avoiding Use-After-Free

```rust
// Rust prevents use-after-free via lifetime system
fn process_data(data: &str) -> &str {
    // Compiler ensures data outlives the returned reference
    data
}

// Box for heap allocation with automatic cleanup
fn create_data() -> Box<String> {
    let s = Box::new(String::from("owned data"));
    s // Automatically freed when dropped
}
```

## Data Race Prevention

```rust
use std::sync::{Arc, Mutex};
use std::thread;

// Arc for shared ownership across threads
let data = Arc::new(Mutex::new(0));

let data_clone = Arc::clone(&data);

thread::spawn(move || {
    let mut d = data_clone.lock().unwrap();
    *d += 1;
});

let mut d = data.lock().unwrap();
*d += 1;

// Only one thread can hold the lock at a time
```

## Safe FFI with Zero-Cost Abstractions

```rust
use std::slice;

// FFI: converting from raw pointers with validation
unsafe fn from_raw_parts<'a>(
    ptr: *const u8,
    len: usize,
) -> Result<&'a [u8], &'static str> {
    if ptr.is_null() && len != 0 {
        return Err("Null pointer with non-zero length");
    }
    Ok(std::slice::from_raw_parts(ptr, len))
}

// Or using std::ptr::copy for efficient memory operations
fn safe_copy(src: &[u8], dst: &mut [u8]) {
    if dst.len() < src.len() {
        panic!("Destination too small");
    }
    dst[..src.len()].copy_from_slice(src);
}
```

## Constrained Mutability

```rust
// Mutex for interior mutability
use std::sync::Mutex;

struct SafeCounter {
    count: Mutex<i32>,
}

impl SafeCounter {
    fn increment(&self) {
        let mut c = self.count.lock().unwrap();
        *c += 1;
    }
    
    fn get(&self) -> i32 {
        *self.count.lock().unwrap()
    }
}

// Cell for interior mutability in single-threaded code
use std::cell::RefCell;

struct Wrapper {
    value: RefCell<String>,
}

impl Wrapper {
    fn update(&self, new_val: &str) {
        *self.value.borrow_mut() = new_val.to_string();
    }
}
```

## Avoiding Integer Overflow

```rust
// Use checked arithmetic
let result = 1000i32.checked_add(2000);

match result {
    Some(value) => println!("Result: {}", value),
    None => println!("Overflow!"),
}

// Or saturating arithmetic for games/graphics
let saturated = 255u8.saturating_add(10); // 255, not wrap
```

This pattern leverages Rust's compiler to prevent memory bugs.