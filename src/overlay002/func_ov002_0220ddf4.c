extern char data_ov002_022ce288[];
extern int func_ov002_0220dd34(int, int);

int func_ov002_0220ddf4(int arg0, int arg1)
{
    int count;

    count = *(int *)(data_ov002_022ce288 + 0x484);

    if (count + 1 < 3)
        return 0;

    return func_ov002_0220dd34(arg0, arg1) != 0;
}
