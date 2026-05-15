use std::process::{self, Command};
use regex::Regex;
use std::fs;

fn swapon() -> String {
    let output = Command::new("swapon")
        .arg("-s")
        .output()
        .expect("Command execution failed");
    String::from_utf8(output.stdout).unwrap()
}

fn swap_check() -> bool {
    let stdout = swapon();
    let swap_pattern = Regex::new(r"^Filename\s+Type\s+Size\s+Used\s+Priority\s*\n\s*\S+").unwrap();

    swap_pattern.is_match(&stdout)
}

fn swap_off() -> Option<String> {
    let stdout = swapon();
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
        .expect("Command execution failed");

    output
}

fn remove_file(path: &str) {
    match fs::remove_file(path) {
        Ok(_) => println!("The swap file ('{path}') was successfully deleted."),
        Err(e) => eprintln!("Failed to delete swap file: {e}"),
    }
}

fn main() {
    if swap_check() {if let Some(path) = swap_off() {remove_file(&path);}}
    else {println!("No swap exists");}
}
