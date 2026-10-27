#include<stdio.h>
#include <unistd.h>
#include <pthread.h>


int counter = 0;


void *increment()
{
	int i;
	for(i=0;i<10000;i++)	
	{
		counter++;
	}
	return NULL;
}

int main()
{

	pthread_t thread1;
	pthread_t thread2;

	pthread_create(&thread1, NULL, increment, NULL);
	pthread_create(&thread2, NULL, increment, NULL);

	pthread_join( thread1, NULL);
	pthread_join( thread2, NULL);

	printf("Counter is %d\n",counter);

	return 0;
}