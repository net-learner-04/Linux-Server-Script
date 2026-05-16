use std::process::{self, Command};
use regex::Regex;
use std::fs;
use std::io::Write;
use sysinfo::System;
use nix::unistd;
use std::path::Path;

fn swapon() -> String {
    let output = Command::new("swapon")
        .arg("-s")
        .output()
        .expect("swapon Command execution failed");
    String::from_utf8(output.stdout).unwrap()
}

fn swap_check(stdout: &str) -> bool {
    let swap_pattern = Regex::new(r"^Filename\s+Type\s+Size\s+Used\s+Priority\s*\n\s*\S+").unwrap();

    swap_pattern.is_match(&stdout)
}

fn swap_off(stdout: &str) -> Option<String> {
    let swap_pattern = Regex::new(r"^Filename\s+Type\s+Size\s+Used\s+Priority\s*\n\s*(?P<path>\S+)").unwrap();
    let output = swap_pattern.captures(&stdout)
        .map(|caps| caps["path"].to_string());

    if output.is_none() {
        println!("The activated swap space cannot be found.");
        process::exit(1);
    }

    Command::new("swapoff")
        .arg("-a")
        .status()
        .expect("swapoff Command execution failed");

    output
}

fn remove_swap_file(path: &str) {
    match fs::remove_file(path) {
        Ok(_) => println!("The swap file ('{path}') was successfully deleted."),
        Err(e) => eprintln!("Failed to delete swap file: {e}"),
    }
}

fn create_swap_file() {
    const GB: u64 = 1024 * 1024 * 1024;

    let block_size = 1024u64 * 1024;

    let mut sys = System::new_all();
    sys.refresh_all();

    let count: u64 = match sys.total_memory() {
        m if m < 4 * GB => 2048,
        m if m < 16 * GB => 4096,
        m if m < 64 * GB => 8192,
        m if m < 256 * GB => 16384,
        _ => 32768,
    };

    let dd = Command::new("dd")
        .arg("if=/dev/zero")
        .arg("of=/swapfile")
        .arg(format!("bs={}", block_size))
        .arg(format!("count={}", count))
        .status()
        .expect("dd Command execution failed");

    if !dd.success() {
        eprintln!("Cannot run the `dd` command");
        process::exit(1);
    }

    Command::new("chmod")
        .args(["600", "/swapfile"])
        .status()
        .expect("chmod Command execution failed");

    Command::new("mkswap")
        .arg("/swapfile")
        .status()
        .expect("mkswap Command execution failed");

    Command::new("swapon")
        .arg("/swapfile")
        .status()
        .expect("swapon Command execution failed");

    let content = fs::read_to_string("/etc/fstab").expect("Failed to read fstab");

    if !content.contains("/swapfile") {
        let mut fstab = fs::OpenOptions::new()
            .append(true)
            .open("/etc/fstab")
            .expect("Failed to open fstab");

        fstab.write_all(b"\n/swapfile swap swap defaults 0 0\n").unwrap();
    }
}

fn remove_fstab(swap_path: &str) {
    let content = fs::read_to_string("/etc/fstab").expect("Failed to read fstab");

    let new_content: String = content
        .lines()
        .filter(|line| !line.contains(swap_path))
        .collect::<Vec<_>>()
        .join("\n");

    let new_content = format!("{}\n", new_content);
    fs::write("/etc/fstab", new_content).expect("Failed to write fstab");
}

fn main() {
    if !unistd::getuid().is_root() {
        eprintln!("Run with sudo");
        process::exit(1);
    }

    let stdout = swapon();

    if swap_check(&stdout) {
        println!("Checking the swap file");

        if let Some(path) = swap_off(&stdout) {
            println!("Deleting swap file");
            remove_swap_file(&path);

            println!("Deleting the /etc/fstab file");
            remove_fstab(&path);
        }
    } else {
        let swap_path = "/swapfile";

        if Path::new(swap_path).exists() {
            println!("Swap file already exists, removing...");
            remove_swap_file(swap_path);
        }

        println!("Deleting the /etc/fstab file");
        remove_fstab(swap_path);

        println!("Creating swap file");
        create_swap_file();
    }
}
