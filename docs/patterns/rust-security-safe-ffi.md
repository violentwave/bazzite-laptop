---
language: rust
domain: security
type: pattern
title: Safe FFI boundary handling
tags: rust, ffi, foreign-function-interface, safety, bindings
---

# Safe FFI Boundary Handling

When calling C libraries from Rust, ensure memory safety and error handling at the boundary.

## Basic FFI Pattern

```rust
use std::ffi::CString;
use std::os::raw::c_char;
use std::ptr;

// Safe wrapper around C function
pub unsafe fn call_c_function(data: &str) -> Result<String, String> {
    // Convert Rust string to C string
    let c_data = CString::new(data).map_err(|_| "Invalid C string")?;
    
    // Call the C function
    let result = unsafe {
        libc::some_function(c_data.as_ptr())
    };
    
    // Check for errors
    if result.is_null() {
        return Err("C function returned null".to_string());
    }
    
    // Convert result back to Rust string
    let c_result = unsafe { CString::from_raw(result) };
    c_result.into_string().map_err(|_| "Invalid UTF-8".to_string())
}
```

## Error Handling with Result

```rust
use std::ffi::CString;
use std::error::Error;

pub enum FfiError {
    InvalidInput(String),
    CError(i32),
    NullPointer,
    EncodingError,
}

impl std::fmt::Display for FfiError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            FfiError::InvalidInput(s) => write!(f, "Invalid input: {}", s),
            FfiError::CError(code) => write!(f, "C error: {}", code),
            FfiError::NullPointer => write!(f, "Null pointer from C"),
            FfiError::EncodingError => write!(f, "UTF-8 encoding error"),
        }
    }
}

impl Error for FfiError {}
```

## Zero-Copy String Handling

```rust
use std::slice;
use std::str::from_utf8;

// When C provides a buffer and length
pub unsafe fn parse_c_buffer(ptr: *const u8, len: usize) -> Result<&str, FfiError> {
    if ptr.is_null() {
        return Err(FfiError::NullPointer);
    }
    
    let slice = unsafe { slice::from_raw_parts(ptr, len) };
    from_utf8(slice).map_err(|_| FfiError::EncodingError)
}
```

## Passing Buffers to C

```rust
use std::mem::MaybeUninit;

pub fn call_c_with_buffer() -> Result<Vec<u8>, FfiError> {
    let mut buffer = vec![0u8; BUFFER_SIZE];
    let mut size: libc::size_t = BUFFER_SIZE;
    
    let result = unsafe {
        libc::fill_buffer(
            buffer.as_mut_ptr(),
            &mut size,
        )
    };
    
    if result != 0 {
        return Err(FfiError::CError(result));
    }
    
    buffer.truncate(size);
    Ok(buffer)
}
```

## Drop Implementation for C Resources

```rust
use std::ffi::CString;

pub struct CHandle {
    handle: *mut libc::c_void,
}

impl CHandle {
    pub fn new() -> Result<Self, FfiError> {
        let handle = unsafe { libc::create_handle() };
        if handle.is_null() {
            return Err(FfiError::NullPointer);
        }
        Ok(Self { handle })
    }
}

// Automatically free C resources
impl Drop for CHandle {
    fn drop(&mut self) {
        unsafe { libc::destroy_handle(self.handle) };
    }
}
```

## Testing FFI Code

```rust
#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_c_string_conversion() {
        let input = "test data";
        let cstr = CString::new(input).unwrap();
        assert_eq!(cstr.to_bytes(), input.as_bytes());
    }
    
    #[test]
    fn test_null_handling() {
        let result = unsafe { parse_c_buffer(std::ptr::null(), 0) };
        assert!(result.is_err());
    }
}
```

This pattern ensures safe Rust/C interoperability.