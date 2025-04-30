lines = ['1\r', '/ # cat /sys/class/gpio/gpio5/value\r']
cmd_response_matches = '\n'.join(lines).strip().replace(' ', '')[0]
print(cmd_response_matches)